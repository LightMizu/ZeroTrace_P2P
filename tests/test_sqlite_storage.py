import time
import pytest
from src.kademlia.http_kad.persistent_storage import SQLiteStorage
from src.kademlia.http_kad.utils import Node, digest


@pytest.fixture
def storage(tmp_path):
    """Create a temporary SQLite storage for testing using tmp_path."""
    db_path = str(tmp_path / "test_kademlia.db")
    storage = SQLiteStorage(db_path=db_path)
    yield storage
    # Cleanup after tests (tmp_path will be removed by pytest automatically)


def test_sqlite_storage_set_get(storage):
    """Test basic set/get operations."""
    key = b'test_key'
    value = "test_value"
    storage[key] = value
    assert storage.get(key) == value


def test_sqlite_storage_get_missing(storage):
    """Test getting a non-existent key."""
    assert storage.get(b'nonexistent') is None
    with pytest.raises(KeyError):
        _ = storage[b'nonexistent']


def test_sqlite_storage_cull(tmp_path):
    """Test that old entries are removed after TTL."""
    db_path = str(tmp_path / "test_cull.db")
    storage = SQLiteStorage(db_path=db_path, ttl=1)  # 1 second TTL
    key = b'temp_key'
    storage[key] = "temp_value"
    assert storage.get(key) == "temp_value"
    
    # Wait for TTL to expire
    time.sleep(1.1)
    storage.cull()
    assert storage.get(key) is None


def test_sqlite_storage_iter(storage):
    """Test iteration over storage items."""
    test_data = {
        b'key1': "value1",
        b'key2': "value2",
        b'key3': "value3"
    }
    
    for key, value in test_data.items():
        storage[key] = value
    
    stored_data = dict(storage)
    assert stored_data == test_data


def test_sqlite_storage_iter_older_than(storage):
    """Test iteration over old items."""
    storage[b'old_key'] = "old_value"
    time.sleep(0.1)
    storage[b'new_key'] = "new_value"
    
    # Get items older than 0.05 seconds
    old_items = dict(storage.iter_older_than(0.05))
    assert b'old_key' in old_items
    assert b'new_key' not in old_items


def test_store_and_get_nodes(storage):
    """Test storing and retrieving nodes."""
    # Create test nodes
    node1_id = digest(b"node1")
    node2_id = digest(b"node2")
    node1 = Node(node1_id, "127.0.0.1", 8000)
    node2 = Node(node2_id, "127.0.0.1", 8001)
    
    # Store nodes
    storage.store_node(node1)
    storage.store_node(node2)
    
    # Retrieve nodes
    nodes = storage.get_known_nodes()
    assert len(nodes) == 2
    
    # Check node properties
    stored_node1 = next(n for n in nodes if n.id == node1_id)
    assert stored_node1.ip == "127.0.0.1"
    assert stored_node1.port == 8000


def test_node_last_seen_filter(storage):
    """Test filtering nodes by last seen timestamp."""
    old_id = digest(b"old_node")
    new_id = digest(b"new_node")
    
    node1 = Node(old_id, "127.0.0.1", 8000)
    storage.store_node(node1)
    
    # Wait a bit
    time.sleep(0.1)
    
    node2 = Node(new_id, "127.0.0.1", 8001)
    storage.store_node(node2)
    
    # Get nodes seen in the last 0.05 seconds
    recent_nodes = storage.get_known_nodes(max_age=0.05)
    assert len(recent_nodes) == 1
    assert recent_nodes[0].id == new_id


def test_clear_storage(storage):
    """Test clearing all data from storage."""
    # Add some data
    storage[b'key1'] = "value1"
    node_id = digest(b"node1")
    storage.store_node(Node(node_id, "127.0.0.1", 8000))
    
    # Clear storage
    storage.clear()
    
    # Verify everything is cleared
    assert list(storage) == []
    assert storage.get_known_nodes() == []


def test_persistence_between_instances(tmp_path):
    """Test that data persists between different instances."""
    db_path = str(tmp_path / "persistence_test.db")
    node_id = digest(b"test_node")
    
    # First instance
    storage1 = SQLiteStorage(db_path=db_path)
    storage1[b'key'] = "value"
    storage1.store_node(Node(node_id, "127.0.0.1", 8000))
    
    # Second instance
    storage2 = SQLiteStorage(db_path=db_path)
    assert storage2.get(b'key') == "value"
    nodes = storage2.get_known_nodes()
    assert len(nodes) == 1
    assert nodes[0].id == node_id
    
    # No explicit cleanup required; tmp_path is cleaned by pytest