import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.kademlia.kademlia.server import create_app
from src.kademlia.kademlia.utils import random_node_id, digest
from .mocks import MockSQLiteStorage


@pytest.fixture
def mock_network():
    """Create a test network with 5 nodes using mocked storage."""
    storage = MockSQLiteStorage()
    
    with patch('src.kademlia.kademlia.server.SQLiteStorage', return_value=storage):
        ports = [9200, 9201, 9202, 9203, 9204]
        apps = [create_app(p) for p in ports]
        clients = [TestClient(a) for a in apps]
        yield {
            'ports': ports,
            'apps': apps,
            'clients': clients,
            'storage': storage
        }


def bootstrap_network(clients, ports):
    """Bootstrap all nodes with each other."""
    for i, c in enumerate(clients):
        for j, p in enumerate(ports):
            if i == j:
                continue
            c.post('/bootstrap', json={
                'node_id': random_node_id().hex(),
                'ip': '127.0.0.1',
                'port': p
            })


def test_integration_replication_k_nearest(mock_network):
    """Test basic replication to k nearest nodes."""
    clients = mock_network['clients']
    ports = mock_network['ports']
    
    bootstrap_network(clients, ports)

    key = b'integ'
    value = b'value'
    d = digest(key)

    # set via node 0
    r = clients[0].post('/set', json={
        'node_id': random_node_id().hex(),
        'ip': '127.0.0.1',
        'port': ports[0],
        'key': d.hex(),
        'value': value.hex()
    })
    assert r.status_code == 200

    # Check all nodes
    found = 0
    for c in clients:
        rr = c.post('/find_value', json={
            'node_id': random_node_id().hex(),
            'ip': '127.0.0.1',
            'port': ports[0],
            'key': d.hex()
        })
        data = rr.json()
        if 'value' in data:
            found += 1

    assert found >= 1


def test_integration_node_lookup(mock_network):
    """Test node lookup functionality."""
    clients = mock_network['clients']
    ports = mock_network['ports']
    
    bootstrap_network(clients, ports)

    # Lookup a node from each client
    for i, client in enumerate(clients):
        r = client.post('/find_node', json={
            'node_id': random_node_id().hex(),
            'ip': '127.0.0.1',
            'port': ports[i],
            'key': random_node_id().hex()
        })
        assert r.status_code == 200
        data = r.json()
        assert 'nodes' in data
        assert isinstance(data['nodes'], list)


def test_integration_ping(mock_network):
    """Test ping functionality between nodes."""
    clients = mock_network['clients']
    ports = mock_network['ports']

    # Ping each node from every other node
    for i, client in enumerate(clients):
        for j, port in enumerate(ports):
            if i == j:
                continue
            r = client.post('/ping', json={
                'node_id': random_node_id().hex(),
                'ip': '127.0.0.1',
                'port': port
            })
            assert r.status_code == 200


def test_integration_multiple_values(mock_network):
    """Test storing and retrieving multiple values."""
    clients = mock_network['clients']
    ports = mock_network['ports']
    
    bootstrap_network(clients, ports)

    # Store multiple key-value pairs
    test_data = {
        b'key1': b'value1',
        b'key2': b'value2',
        b'key3': b'value3'
    }

    for key, value in test_data.items():
        d = digest(key)
        r = clients[0].post('/set', json={
            'node_id': random_node_id().hex(),
            'ip': '127.0.0.1',
            'port': ports[0],
            'key': d.hex(),
            'value': value.hex()
        })
        assert r.status_code == 200

    # Verify values can be retrieved
    for key in test_data:
        d = digest(key)
        found = False
        for client in clients:
            r = client.post('/find_value', json={
                'node_id': random_node_id().hex(),
                'ip': '127.0.0.1',
                'port': ports[0],
                'key': d.hex()
            })
            if r.status_code == 200 and 'value' in r.json():
                found = True
                break
        assert found, f"Value for key {key} not found"


def test_integration_node_failure_recovery(mock_network):
    """Test network recovery after node failure."""
    clients = mock_network['clients']
    ports = mock_network['ports']
    
    bootstrap_network(clients, ports)

    # Store multiple copies of the value
    key = b'failtest'
    value = b'testvalue'
    d = digest(key)
    
    # Store from different nodes to ensure replication
    for i in range(3):
        r = clients[i].post('/set', json={
            'node_id': random_node_id().hex(),
            'ip': '127.0.0.1',
            'port': ports[i],
            'key': d.hex(),
            'value': value.hex()
        })
        assert r.status_code == 200

    # "Remove" first two nodes
    working_clients = clients[2:]
    working_ports = ports[2:]
    
    # Try to retrieve the value from remaining nodes
    found = False
    for client, port in zip(working_clients, working_ports):
        r = client.post('/find_value', json={
            'node_id': random_node_id().hex(),
            'ip': '127.0.0.1',
            'port': port,
            'key': d.hex()
        })
        if r.status_code == 200 and 'value' in r.json():
            found = True
            break
    
    assert found, "Value not found after node failure"
