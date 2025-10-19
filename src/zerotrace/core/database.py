from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from zerotrace.core.models import Contact, Message, ForwardMessage, Base

DATABASE_URL = "sqlite+aiosqlite:///zerotrace.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False) # type: ignore

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class ContactManager:
    async def add_contact(self, identifier: str, kem_public_key: str , sign_public_key: str, addr: str, name: str | None = None):
        async with AsyncSessionLocal() as session:# type: ignore
            exists = await session.scalar(select(Contact).filter_by(identifier=identifier))
            if not exists:
                contact = Contact(identifier=identifier, name=name, kem_public_key=kem_public_key, sign_public_key=sign_public_key, addr=addr)
                session.add(contact)
                await session.commit()
                return contact
            return exists

    async def get_contact(self, identifier: str) -> Contact | None:
        async with AsyncSessionLocal() as session:# type: ignore
            return await session.scalar(select(Contact).filter_by(identifier=identifier))

    async def list_contacts(self) -> list[Contact]:
        async with AsyncSessionLocal() as session:# type: ignore
            result = await session.scalars(select(Contact))
            return result.all()


class MessageManager:
    async def add_message(self, **kwargs) -> Message:
        async with AsyncSessionLocal() as session:# type: ignore
            msg = Message(**kwargs)
            session.add(msg)
            await session.commit()
            return msg

    async def get_message(self, sender_id: str) -> Message | None:
        async with AsyncSessionLocal() as session:# type: ignore
            return await session.scalar(select(Message).filter_by(sender_id=sender_id))


class ForwardMessageManager:
    async def add_forward_message(self, **kwargs) -> ForwardMessage:
        async with AsyncSessionLocal() as session:# type: ignore
            fwd = ForwardMessage(**kwargs)
            session.add(fwd)
            await session.commit()
            return fwd

    async def get_for_contact(self, recipient_identifier: str) -> list[ForwardMessage]:
        """Возвращает все пересланные сообщения для данного контакта."""
        async with AsyncSessionLocal() as session:# type: ignore
            result = await session.scalars(
                select(ForwardMessage).filter_by(recipient_identifier=recipient_identifier)
            )
            return result.all()

    async def delete_forward_message(self, recipient_identifier: str) -> bool:
        async with AsyncSessionLocal() as session:# type: ignore
            fwd = await session.scalar(select(ForwardMessage).filter_by(recipient_identifier=recipient_identifier))
            if fwd:
                await session.delete(fwd)
                await session.commit()
                return True
            return False

