import sqlite3
import time
import json
from typing import Iterator, Tuple, Optional
from .utils import Node


class SQLiteStorage:
    def __init__(self, db_path: str = "kademlia.db", ttl: int = 604800):
        self.db_path = db_path
        self.ttl = ttl
        # Create tables in first connection
        with self._connect() as conn:
            self._ensure_tables(conn)

    def _connect(self):
        """Return an sqlite3 connection. If db_path is a URI (starts with 'file:'),
        open with uri=True so shared in-memory DBs work (e.g. file:foo?mode=memory&cache=shared).
        """
        if isinstance(self.db_path, str) and self.db_path.startswith("file:"):
            return sqlite3.connect(self.db_path, uri=True)
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self, conn):
        """Create tables if they don't exist in the given connection."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key BLOB PRIMARY KEY,
                value BLOB,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS known_nodes (
                node_id TEXT PRIMARY KEY,
                ip TEXT,
                port INTEGER,
                last_seen REAL
            )
        """)

    def __setitem__(self, key: bytes, value):
        """Store a key-value pair in the database."""
        if isinstance(value, bytes):
            # Store bytes as hex string
            value_to_store = value.hex()
            is_bytes = True
        else:
            value_to_store = value
            is_bytes = False

        with self._connect() as conn:
            self._ensure_tables(conn)
            conn.execute(
                "INSERT OR REPLACE INTO kv_store (key, value, timestamp) VALUES (?, ?, ?)",
                (key, json.dumps({'value': value_to_store, 'is_bytes': is_bytes}), time.monotonic())
            )
            conn.commit()

    def __getitem__(self, key: bytes):
        """Retrieve a value by key from the database."""
        self.cull()
        with self._connect() as conn:
            self._ensure_tables(conn)
            cursor = conn.execute(
                "SELECT value FROM kv_store WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(key)
            
            data = json.loads(row[0])
            if data['is_bytes']:
                return bytes.fromhex(data['value'])
            return data['value']

    def get(self, key: bytes, default=None):
        """Get a value from storage by key with a default value."""
        try:
            return self[key]
        except KeyError:
            return default

    def cull(self):
        """Remove expired entries."""
        with self._connect() as conn:
            self._ensure_tables(conn)
            min_time = time.monotonic() - self.ttl
            conn.execute(
                "DELETE FROM kv_store WHERE timestamp < ?",
                (min_time,)
            )
            conn.commit()

    def store_node(self, node: Node):
        """Store information about a known node."""
        with self._connect() as conn:
            self._ensure_tables(conn)
            conn.execute(
                "INSERT OR REPLACE INTO known_nodes (node_id, ip, port, last_seen) VALUES (?, ?, ?, ?)",
                (node.id, node.ip, node.port, time.monotonic())
            )
            conn.commit()

    def get_known_nodes(self, max_age: Optional[float] = None) -> list[Node]:
        """Retrieve list of known nodes, optionally filtering by age."""
        with self._connect() as conn:
            self._ensure_tables(conn)
            query = "SELECT node_id, ip, port FROM known_nodes"
            params = []
            
            if max_age is not None:
                min_time = time.monotonic() - max_age
                query += " WHERE last_seen >= ?"
                params.append(min_time)

            cursor = conn.execute(query, params)
            return [Node(node_id, ip, port) for node_id, ip, port in cursor.fetchall()]

    def iter_older_than(self, seconds_old: int) -> Iterator[Tuple[bytes, object]]:
        """Iterate over items older than the specified time."""
        min_birthday = time.monotonic() - seconds_old
        with self._connect() as conn:
            self._ensure_tables(conn)
            cursor = conn.execute(
                "SELECT key, value FROM kv_store WHERE timestamp < ?",
                (min_birthday,)
            )
            for key, value in cursor:
                data = json.loads(value)
                if data['is_bytes']:
                    yield key, bytes.fromhex(data['value'])
                else:
                    yield key, data['value']

    def __iter__(self):
        """Iterate over all non-expired items in storage."""
        self.cull()
        with self._connect() as conn:
            self._ensure_tables(conn)
            cursor = conn.execute("SELECT key, value FROM kv_store")
            for key, value in cursor:
                data = json.loads(value)
                if data['is_bytes']:
                    yield key, bytes.fromhex(data['value'])
                else:
                    yield key, data['value']

    def clear(self):
        """Clear all data from storage."""
        with self._connect() as conn:
            self._ensure_tables(conn)
            conn.execute("DELETE FROM kv_store")
            conn.execute("DELETE FROM known_nodes")
            conn.commit()