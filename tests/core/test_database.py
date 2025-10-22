import pytest_asyncio
import pytest
from datetime import datetime
from sqlalchemy import text

from src.zerotrace.core.database import Database


@pytest_asyncio.fixture(scope="module")
async def db():
    """Создаёт временную in-memory базу для тестов."""
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_add_and_get_contact(db: Database):
    await db.add_contact(
        identifier="alice",
        kem_public_key="kem123",
        sign_public_key="sig123",
        addr="127.0.0.1",
        name="Alice"
    )

    contact = await db.get_contact("alice")
    assert contact is not None
    assert contact.name == "Alice"
    assert contact.addr == "127.0.0.1"

    contacts = await db.list_contacts()
    assert len(contacts) == 1


@pytest.mark.asyncio
async def test_add_and_get_message(db: Database):
    msg = await db.add_message(sender_id="alice", content="Hello", timestamp=datetime.utcnow())
    result = await db.get_message("alice")
    assert result is not None
    assert result.content == "Hello"
    assert msg.id == result.id


@pytest.mark.asyncio
async def test_forward_message_crud(db: Database):
    await db.add_forward_message(recipient_identifier="bob",shared_secret_ciphertext="", message_ciphertext="Forwarded text", nonce="", signature="")

    result = await db.get_for_contact("bob")
    assert len(result) == 1
    assert result[0].recipient_identifier == "bob"

    deleted = await db.delete_forward_message("bob")
    assert deleted is True

    result_after = await db.get_for_contact("bob")
    assert len(result_after) == 0


@pytest.mark.asyncio
async def test_cleanup_trigger_for_seen_history(db: Database):
    async with db.engine.begin() as conn:
        # старее 2 дней — должно удалиться
        await conn.execute(text("""
            INSERT INTO seen_history (signature, timestamp)
            VALUES ('old', datetime('now', '-2 days'));
        """))
        # новая запись
        await conn.execute(text("""
            INSERT INTO seen_history (signature, timestamp)
            VALUES ('new', datetime('now'));
        """))
        # проверяем, что осталась только новая
        rows = await conn.execute(text("SELECT signature FROM seen_history;"))
        result = [r[0] for r in rows]
        assert "old" not in result
        assert "new" in result


@pytest.mark.asyncio
async def test_close_disposes_engine(db: Database):
    await db.close()
    assert db.engine.dispose
