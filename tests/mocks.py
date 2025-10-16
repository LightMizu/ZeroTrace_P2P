import time
from typing import Iterator, Tuple, Optional, Any, Dict, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from src.kademlia.http_kad.utils import Node


class MockSQLiteStorage:
    """
    Mock storage that mimics SQLiteStorage but keeps everything in memory.
    This mock completely avoids any file system operations and SQLite usage.
    """
    
    def __init__(self, db_path: Optional[str] = None, ttl: int = 604800):
        """
        Initialize mock storage. Ignores db_path completely.
        
        Args:
            db_path: Ignored. Included only for compatibility.
            ttl: Time to live for stored items in seconds.
        """
        self.ttl = ttl
        self._data: Dict[bytes, Tuple[float, Any]] = {}  # key -> (timestamp, value)
        self._nodes: Dict[bytes, Dict[str, Any]] = defaultdict(dict)  # node_id -> {ip, port, last_seen}
    
    def __setitem__(self, key: bytes, value: Any) -> None:
        """
        Store a key-value pair.
        
        Args:
            key: The key as bytes
            value: The value to store
        """
        self._data[key] = (time.monotonic(), value)
        self.cull()

    def __getitem__(self, key: bytes) -> Any:
        """
        Retrieve a value by key.
        
        Args:
            key: The key to look up
            
        Returns:
            The stored value
            
        Raises:
            KeyError: If key not found or expired
        """
        self.cull()
        if key not in self._data:
            raise KeyError(key)
        _, value = self._data[key]
        return value

    def get(self, key: bytes, default: Any = None) -> Any:
        """
        Get a value with a default.
        
        Args:
            key: The key to look up
            default: Value to return if key not found
            
        Returns:
            The stored value or default
        """
        try:
            return self[key]
        except KeyError:
            return default

    def cull(self) -> None:
        """Remove expired entries."""
        now = time.monotonic()
        
        # Cull expired key-value pairs
        expired_keys = [
            k for k, (timestamp, _) in self._data.items()
            if now - timestamp > self.ttl
        ]
        for k in expired_keys:
            del self._data[k]

        # Cull expired nodes
        expired_nodes = [
            node_id for node_id, data in self._nodes.items()
            if now - data['last_seen'] > self.ttl
        ]
        for node_id in expired_nodes:
            del self._nodes[node_id]

    def store_node(self, node: 'Node') -> None:
        """
        Store information about a node.
        
        Args:
            node: The Node instance to store
        """
        self._nodes[node.id] = {
            'ip': node.ip,
            'port': node.port,
            'last_seen': time.monotonic()
        }

    def get_known_nodes(self, max_age: Optional[float] = None) -> list['Node']:
        """
        Get list of known nodes.
        
        Args:
            max_age: Optional maximum age in seconds
            
        Returns:
            List of Node instances
        """
        from src.kademlia.http_kad.utils import Node
        
        now = time.monotonic()
        result = []
        
        for node_id, data in self._nodes.items():
            age = now - data['last_seen']
            if max_age is None or age <= max_age:
                result.append(Node(node_id, data['ip'], data['port']))
        
        return result

    def iter_older_than(self, seconds_old: int) -> Iterator[Tuple[bytes, Any]]:
        """
        Iterate over items older than specified time.
        
        Args:
            seconds_old: Age threshold in seconds
            
        Returns:
            Iterator of (key, value) tuples
        """
        min_time = time.monotonic() - seconds_old
        return (
            (k, v[1]) for k, v in self._data.items()
            if v[0] < min_time
        )

    def __iter__(self) -> Iterator[Tuple[bytes, Any]]:
        """
        Iterate over all non-expired items.
        
        Returns:
            Iterator of (key, value) tuples
        """
        self.cull()
        return ((k, v[1]) for k, v in self._data.items())

    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()
        self._nodes.clear()