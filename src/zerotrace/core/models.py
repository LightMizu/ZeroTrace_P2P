from sqlalchemy import Column, Float, String, Integer, func, DateTime
from sqlalchemy.orm import declarative_base
from typing import TypedDict, Mapping, Literal
# Базовый класс для моделей
Base = declarative_base()

# Определяем таблицу через ORM-модель


class Contact(Base):
    __tablename__ = "contacts"

    identifier = Column(String, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    addr = Column(String, nullable=False)
    kem_public_key = Column(String, nullable=False)
    sign_public_key = Column(String, nullable=False)



class SeenHistory(Base):
    __tablename__ = "seen_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    signature = Column(String, nullable=False,unique=True)
    timestamp = Column(Float, server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    recipient_id = Column(String, nullable=True)  # For self-sent messages


class ForwardMessage(Base):
    __tablename__ = "forward_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient_identifier = Column(String, index=True, nullable=False)
    shared_secret_ciphertext = Column(String, nullable=False)
    message_ciphertext = Column(String, nullable=False)
    nonce = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    signature = Column(String, unique=True, nullable=False)


PublicKeyName = Literal["kem.public", "sig.public"]
EncryptedKeyName = Literal["kem.private", "sig.private"]


class KeyBundle(TypedDict):
    salt: str
    nonce: str
    public_keys: Mapping[PublicKeyName, str]
    encrypted_keys: Mapping[EncryptedKeyName, str]
    keycheck: str