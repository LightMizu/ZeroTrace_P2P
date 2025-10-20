from sqlalchemy import select,text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from zerotrace.core.models import Contact, Message, ForwardMessage, SeenHistory, Base

class SeenHistoryManager:
    """Менеджер для работы с таблицей seen_history."""

    SessionLocal: "sessionmaker[AsyncSession]"  # для типизации Pyright/MyPy #type: ignore

    async def add_entry(self, signature: str, timestamp: float | None = None) -> SeenHistory:
        """Добавляет новую запись, если такой signature ещё нет."""
        async with self.SessionLocal() as session:
            exists = await session.scalar(select(SeenHistory).filter_by(signature=signature))
            if not exists:
                entry = SeenHistory(signature=signature, timestamp=timestamp)
                session.add(entry)
                await session.commit()
                return entry
            return exists

    async def get_entry(self, signature: str) -> SeenHistory | None:
        """Получает запись по signature."""
        async with self.SessionLocal() as session:
            return await session.scalar(select(SeenHistory).filter_by(signature=signature))

class ContactManager:
    SessionLocal: "sessionmaker[AsyncSession]"  # для типизации Pyright/MyPy #type: ignore
    async def add_contact(self, identifier: str, kem_public_key: str, sign_public_key: str, addr: str, name: str | None = None):
        
        async with self.SessionLocal() as session:
            exists = await session.scalar(select(Contact).filter_by(identifier=identifier))
            if not exists:
                contact = Contact(
                    identifier=identifier,
                    name=name,
                    kem_public_key=kem_public_key,
                    sign_public_key=sign_public_key,
                    addr=addr,
                )
                session.add(contact)
                await session.commit()
                return contact
            return exists

    async def get_contact(self, identifier: str) -> Contact | None:
        
        async with self.SessionLocal() as session:
            return await session.scalar(select(Contact).filter_by(identifier=identifier))

    async def list_contacts(self) -> list[Contact]:
        
        async with self.SessionLocal() as session:
            result = await session.scalars(select(Contact))
            return list(result.all())


class MessageManager:
    SessionLocal: "sessionmaker[AsyncSession]"  # для типизации Pyright/MyPy #type: ignore
    async def add_message(self, **kwargs) -> Message:
        
        async with self.SessionLocal() as session:
            msg = Message(**kwargs)
            session.add(msg)
            await session.commit()
            return msg

    async def get_message(self, sender_id: str) -> Message | None:
        
        async with self.SessionLocal() as session:
            return await session.scalar(select(Message).filter_by(sender_id=sender_id))
    
    async def list_messages(self, sender_id: str | None = None) -> list[Message]:
        """List all messages, optionally filtered by sender_id."""
        async with self.SessionLocal() as session:
            if sender_id:
                result = await session.scalars(select(Message).filter_by(sender_id=sender_id))
            else:
                result = await session.scalars(select(Message))
            return list(result.all())


class ForwardMessageManager:
    SessionLocal: "sessionmaker[AsyncSession]"  # для типизации Pyright/MyPy #type: ignore
    async def add_forward_message(self, **kwargs) -> ForwardMessage:
        
        async with self.SessionLocal() as session:
            fwd = ForwardMessage(**kwargs)
            session.add(fwd)
            await session.commit()
            return fwd

    async def get_for_contact(self, recipient_identifier: str) -> list[ForwardMessage]:
        """Возвращает все пересланные сообщения для данного контакта."""
        
        async with self.SessionLocal() as session:
            result = await session.scalars(
                select(ForwardMessage).filter_by(recipient_identifier=recipient_identifier)
            )
            return list(result.all())

    async def delete_forward_message(self, recipient_identifier: str) -> bool:
        
        async with self.SessionLocal() as session:
            fwd = await session.scalar(select(ForwardMessage).filter_by(recipient_identifier=recipient_identifier))
            if fwd:
                await session.delete(fwd)
                await session.commit()
                return True
            return False

class Database(ContactManager, MessageManager, ForwardMessageManager, SeenHistoryManager):

    """Общий класс, объединяющий менеджеры и управление соединением."""

    def __init__(self, url: str = "sqlite+aiosqlite:///zerotrace.db", echo: bool = False):
        self.engine = create_async_engine(url, echo=echo)
        self.SessionLocal = sessionmaker(
            bind=self.engine, #type: ignore
            class_=AsyncSession,
            expire_on_commit=False,
        ) #type: ignore

    async def init(self):
        """Создать все таблицы и триггеры."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self._create_triggers()

    async def _create_triggers(self):
        async with self.engine.begin() as conn:
            # Очистка seen_history старше 1 дня
            await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS delete_old_history
            AFTER INSERT ON seen_history
            BEGIN
                DELETE FROM seen_history
                WHERE timestamp < datetime('now', '-1 day');
            END;
            """))

            # Очистка forward_messages старше 7 дней
            await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS delete_old_forward_messages
            AFTER INSERT ON forward_messages
            BEGIN
                DELETE FROM forward_messages
                WHERE created_at < datetime('now', '-7 days');
            END;
            """))

    async def close(self):
        """Закрыть соединение с базой."""
        await self.engine.dispose()