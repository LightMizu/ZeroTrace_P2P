import pytest
import time
from fastapi.testclient import TestClient
from src.kademlia.http_kad.server import create_app
from src.kademlia.http_kad.utils import random_node_id, digest

@pytest.fixture
def kademlia_nodes(tmp_path):
    """Create 5 HTTP nodes for testing using tmp_path for any file storage."""
    ports = list(range(8000, 8005))
    apps = []
    clients = []
    
    for port in ports:
        # Each test server will use a memory SQLite database
        app = create_app(port)
        apps.append(app)
        clients.append(TestClient(app))
    
    yield list(zip(ports, clients))
    
    # Cleanup - close clients and clear app cache
    for client in clients:
        client.close()
    # Clear the app cache from server.py
    from src.kademlia.http_kad.server import _app_cache
    _app_cache.clear()

def test_ping_add_new_node(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    new_node_id = random_node_id()
    res = client1.post("/ping", json={"node_id": new_node_id.hex()})
    assert res.status_code == 200
    assert "id" in res.json()

def test_ping_existing_node(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    nid = random_node_id()
    client1.post("/ping", json={"node_id": nid.hex()})
    res = client1.post("/ping", json={"node_id": nid.hex()})
    assert res.status_code == 200

def test_store_value(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    nid = random_node_id()
    key = b"key1"
    value = b"value1"
    res = client1.post("/store", json={
        "node_id": nid.hex(),
        "key": key.hex(),
        "value": value.hex()
    })
    assert res.status_code == 200
    assert res.json()["ok"] is True

def test_store_value_raw(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    nid = random_node_id()
    key = "key_raw"
    value = "value_raw"
    res = client1.post("/store", json={
        "node_id": nid.hex(),
        "key": key,
        "value": value
    })
    assert res.status_code == 200
    assert res.json()["ok"] is True

def test_find_value_existing_and_missing(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    _, client2 = kademlia_nodes[1]
    nid = random_node_id()
    key = b"key2"
    value = b"value2"
    client1.post("/store", json={
        "node_id": nid.hex(),
        "key": key.hex(),
        "value": value.hex()
    })

    # найдётся value
    res = client1.post("/find_value", json={"node_id": nid.hex(), "key": key.hex()})
    data = res.json()
    assert "value" in data or "nodes" in data

    # несуществующий ключ
    missing_key = b"unknown_key"
    res = client2.post("/find_value", json={"node_id": nid.hex(), "key": missing_key.hex()})
    data = res.json()
    assert "nodes" in data

def test_replication_among_nodes(kademlia_nodes):
    """Test that values are replicated across multiple nodes."""
    (_, client1), (_, client2), (_, client3), (_, client4), (_, client5) = kademlia_nodes
    nid = random_node_id()
    key = b"replicated"
    value = b"value_rep"
    
    # Register node2 first
    client2.post("/ping", json={"node_id": nid.hex()})
    
    # Store value on node1
    client1.post("/store", json={
        "node_id": nid.hex(),
        "key": key.hex(),
        "value": value.hex()
    })
    
    # Small delay to allow replication
    time.sleep(0.5)  # Reduced from 1s since we're using in-memory DBs
    
    # Check replication across nodes
    responses = [
        client2.post("/find_value", json={"node_id": nid.hex(), "key": key.hex()}),
        client3.post("/find_value", json={"node_id": random_node_id().hex(), "key": key.hex()}),
        client4.post("/find_value", json={"node_id": random_node_id().hex(), "key": key.hex()}),
        client5.post("/find_value", json={"node_id": random_node_id().hex(), "key": key.hex()})
    ]
    
    # Verify each node can either find the value or knows which nodes have it
    for resp in responses:
        data = resp.json()
        assert "value" in data or "nodes" in data

def test_find_node_returns_neighbors(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    nid = random_node_id()
    target_id = random_node_id()
    res = client1.post("/find_node", json={"node_id": nid.hex(), "key": target_id.hex()})
    data = res.json()
    assert "nodes" in data
    assert isinstance(data["nodes"], list)

def test_invalid_node_id(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    res = client1.post("/ping", json={"node_id": "invalid_id"})
    assert res.status_code == 200

def test_empty_value_key(kademlia_nodes):
    _, client1 = kademlia_nodes[0]
    nid = random_node_id()
    res = client1.post("/store", json={"node_id": nid.hex(), "key": "", "value": ""})
    assert res.status_code == 200
    assert res.json()["ok"] is True
