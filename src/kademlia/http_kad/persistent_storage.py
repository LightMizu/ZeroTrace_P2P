import time
import json
from typing import Iterator, Tuple, Optional, List

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, LargeBinary, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import NoResultFound

from .utils import Node, random_node_id

Base = declarative_base()


class KVStore(Base):
    __tablename__ = "kv_store"
    key = Column(LargeBinary, primary_key=True)
    value = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)


class KnownNode(Base):
    __tablename__ = "known_nodes"
    node_id = Column(String, primary_key=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    last_seen = Column(Float, nullable=False)


class SQLiteStorage:
    def __init__(self, db_path: Optional[str] = None, ttl: int = 604800):
        """
        db_path — путь к базе (например 'sqlite:///kademlia.db').
        Если None или пусто — используется база в памяти (sqlite:///:memory:).
        ttl — время жизни ключа в секундах.
        """
        if not db_path:
            db_path =f"sqlite:///file:{random_node_id().hex()}?mode=memory&cache=shared&uri=true"
        else:
            db_path = f"sqlite:///{db_path}"
        # Для shared in-memory SQLite можно использовать:
        # db_path = "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"
        # но это нужно только если база должна шариться между потоками.

        self.engine = create_engine(db_path, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.ttl = ttl

    # ------------------------------
    # KV-хранилище
    # ------------------------------

    def __setitem__(self, key: bytes, value):
        if isinstance(value, bytes):
            value_to_store = value.hex()
            is_bytes = True
        else:
            value_to_store = value
            is_bytes = False

        json_value = json.dumps({'value': value_to_store, 'is_bytes': is_bytes})
        with self.Session() as session:
            obj = KVStore(key=key, value=json_value, timestamp=time.monotonic())
            session.merge(obj)
            session.commit()

    def __getitem__(self, key: bytes):
        self.cull()
        with self.Session() as session:
            kv = session.query(KVStore).filter(KVStore.key == key).one_or_none()
            if kv is None:
                raise KeyError(key)
            data = json.loads(kv.value)
            return bytes.fromhex(data['value']) if data['is_bytes'] else data['value']

    def get(self, key: bytes, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def cull(self):
        min_time = time.monotonic() - self.ttl
        with self.Session() as session:
            session.query(KVStore).filter(KVStore.timestamp < min_time).delete()
            session.commit()

    # ------------------------------
    # Узлы (Node)
    # ------------------------------

    def store_node(self, node: Node):
        with self.Session() as session:
            obj = KnownNode(
                node_id=node.id,
                ip=node.ip,
                port=node.port,
                last_seen=time.monotonic(),
            )
            session.merge(obj)
            session.commit()

    def get_known_nodes(self, max_age: Optional[float] = None) -> List[Node]:
        with self.Session() as session:
            query = session.query(KnownNode)
            if max_age is not None:
                min_time = time.monotonic() - max_age
                query = query.filter(KnownNode.last_seen >= min_time)
            rows = query.all()
            return [Node(row.node_id, row.ip, row.port) for row in rows]

    # ------------------------------
    # Итераторы
    # ------------------------------

    def iter_older_than(self, seconds_old: int) -> Iterator[Tuple[bytes, object]]:
        min_birthday = time.monotonic() - seconds_old
        with self.Session() as session:
            for kv in session.query(KVStore).filter(KVStore.timestamp < min_birthday):
                data = json.loads(kv.value)
                yield kv.key, bytes.fromhex(data['value']) if data['is_bytes'] else data['value']

    def __iter__(self):
        self.cull()
        with self.Session() as session:
            for kv in session.query(KVStore).all():
                data = json.loads(kv.value)
                yield kv.key, bytes.fromhex(data['value']) if data['is_bytes'] else data['value']

    def clear(self):
        with self.Session() as session:
            session.query(KVStore).delete()
            session.query(KnownNode).delete()
            session.commit()
