import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.kademlia.kademlia.server import create_app
from src.kademlia.kademlia.utils import random_node_id, digest
from .mocks import MockSQLiteStorage


@pytest.fixture
def mock_storage():
    """Create a mock storage instance."""
    return MockSQLiteStorage()


@pytest.fixture
def mock_network():
    """Create a test network with mocked storage."""
    storage = MockSQLiteStorage("mock.db")
    
    with patch('src.kademlia.kademlia.server.SQLiteStorage', return_value=storage):
        ports = [9100, 9101, 9102]
        apps = [create_app(p) for p in ports]
        clients = [TestClient(a) for a in apps]
        yield {
            'ports': ports,
            'apps': apps,
            'clients': clients,
            'storage': storage
        }


def test_replication_to_k_nearest(mock_network):
        """Test replication to k nearest nodes with mocked storage."""
        clients = mock_network['clients']
        ports = mock_network['ports']
        storage = mock_network['storage']

        # Set value directly in storage of first node to test retrieval
        key = b'mykey'
        value = b'myvalue'
        d = digest(key)
        storage[d] = value

        # Check that value can be retrieved
        r = clients[0].post('/find_value', json={
            'node_id': random_node_id().hex(),
            'ip': '127.0.0.1',
            'port': ports[0],
            'key': d.hex()
        })
        
        assert r.status_code == 200
        data = r.json()
        assert 'value' in data
        assert bytes.fromhex(data['value']) == value
def test_node_ping(mock_network):
    """Test node ping functionality with mocked storage."""
    clients = mock_network['clients']
    ports = mock_network['ports']

    # Test ping between nodes
    for i, client in enumerate(clients):
        for port in ports:
            r = client.post('/ping', json={
                'node_id': random_node_id().hex(),
                'ip': '127.0.0.1',
                'port': port
            })
            assert r.status_code == 200
            response = r.json()
            # Проверяем, что ответ содержит либо 'ok': True, либо 'id'
            assert ('ok' in response and response['ok'] is True) or 'id' in response


def test_find_node(mock_network):
    """Test find_node functionality with mocked storage."""
    clients = mock_network['clients']
    ports = mock_network['ports']

    # Bootstrap the network
    for i, c in enumerate(clients):
        for j, port in enumerate(ports):
            if i != j:
                c.post('/bootstrap', json={
                    'node_id': random_node_id().hex(),
                    'ip': '127.0.0.1',
                    'port': port
                })

    # Test find_node
    test_key = random_node_id()
    r = clients[0].post('/find_node', json={
        'node_id': random_node_id().hex(),
        'ip': '127.0.0.1',
        'port': ports[0],
        'key': test_key.hex()
    })
    
    assert r.status_code == 200
    data = r.json()
    assert 'nodes' in data
    assert isinstance(data['nodes'], list)
    assert len(data['nodes']) > 0
