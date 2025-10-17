import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.zerotrace.kademlia.server import create_app
from src.zerotrace.kademlia.utils import random_node_id, digest
from .mocks import MockSQLiteStorage


@pytest.fixture
def mock_network():
    """Create a test network with 5 nodes using mocked storage."""
    storage = MockSQLiteStorage()
    
    with patch('src.zerotrace.kademlia.server.SQLiteStorage', return_value=storage):
        ports = [9200, 9201, 9202, 9203, 9204]
        apps = [create_app(p) for p in ports]
        clients = [TestClient(a) for a in apps]
        yield {
            'ports': ports,
            'apps': apps,
            'clients': clients,
            'storage': storage
        }


def test_triangle_network(tmp_path):
    # Три ноды (A, B, C). ksize=1 чтобы репликация шла только на ближайшую ноду.
    ports = [9101, 9102, 9103]
    apps = [create_app(port=ports[i], db_path=str(tmp_path / f"node{i}.db"), ksize=1, allow_broadcast=False) for i in range(3)]
    clients = [TestClient(a) for a in apps]

    # Получаем node_id каждой ноды
    node_ids = []
    for client in clients:
        resp = client.get("/id")
        assert resp.status_code == 200
        node_ids.append(resp.json()["id"])

    # Соединяем NodeA <-> NodeB и NodeB <-> NodeC, но не NodeA <-> NodeC
    # Bootstrap: NodeA с NodeB, NodeB с NodeC (use target node ids)
    # Bootstrap A->B and B->C (no direct A<->C)
    clients[0].post("/bootstrap", json={"node_id": node_ids[1], "ip": "127.0.0.1", "port": ports[1]})
    clients[1].post("/bootstrap", json={"node_id": node_ids[2], "ip": "127.0.0.1", "port": ports[2]})

    # Кладём значение на NodeA через /set (репликация)
    key = "74657374"  # hex для b"test"
    value = "76616c31"  # hex для b"val1"
    clients[0].post("/set", json={"node_id": node_ids[0], "key": key, "value": value})

    # Проверяем, что NodeB может получить значение через find_value (должен работать)
    # NodeB should be able to find the value (replicated to its nearest)
    resp_b = clients[1].post("/find_value", json={"node_id": node_ids[0], "key": key})
    assert resp_b.status_code == 200
    assert resp_b.json().get("value") == value

    # Проверяем, что NodeC НЕ может получить значение напрямую (нет bootstrap с NodeA)
    resp_c = clients[2].post("/find_value", json={"node_id": node_ids[2], "key": key})
    # NodeC не должен иметь value (нет прямого соединения с A)
    assert resp_c.status_code == 200
    assert "value" not in resp_c.json()

def test_find_value_returns_value(tmp_path):
    # Создаём приложение и клиента
    db_path = str(tmp_path / "test_find_value.db")
    app = create_app(port=9000, db_path=db_path)
    client = TestClient(app)

    # Кладём значение напрямую через /store
    key = "6b6579"  # hex для b"key"
    value = "76616c"  # hex для b"val"
    node_id = "01" * 20  # фейковый node_id

    resp = client.post("/store", json={
        "node_id": node_id,
        "key": key,
        "value": value
    })
    assert resp.status_code == 200

    # Получаем значение через /find_value
    resp = client.post("/find_value", json={
        "node_id": node_id,
        "key": key
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "value" in data
    assert data["value"] == value

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
    
def test_replication_counts_for_various_k(tmp_path):
    """For k in [1,2,3] create a small 5-node network and record how many
    nodes hold a value after a /set. We assert the number of replicas is
    non-decreasing as k increases.
    """
    ks = [1, 2, 3]
    counts = []

    for k in ks:
        ports = [9501, 9502, 9503, 9504, 9505]
        apps = [create_app(port=ports[i], db_path=str(tmp_path / f"rk5_k{k}_node{i}.db"), ksize=k, allow_broadcast=False) for i in range(5)]
        clients = [TestClient(a) for a in apps]

        # fully bootstrap
        node_ids = []
        for c in clients:
            r = c.get('/id')
            assert r.status_code == 200
            node_ids.append(r.json()['id'])
        for i, c in enumerate(clients):
            for j, p in enumerate(ports):
                if i == j:
                    continue
                c.post('/bootstrap', json={'node_id': node_ids[j], 'ip': '127.0.0.1', 'port': p})

        # store a value on node 0
        key = 'deadbe'
        value = 'cafebe'
        r = clients[0].post('/set', json={'node_id': node_ids[0], 'key': key, 'value': value})
        assert r.status_code == 200

        # count how many nodes can return the value
        found = 0
        for c in clients:
            rr = c.post('/find_value', json={'node_id': node_ids[0], 'key': key})
            data = rr.json()
            if 'value' in data and data['value'] == value:
                found += 1
        counts.append(found)

    # non-decreasing counts as k increases
    assert counts[0] >= 1
    assert counts == sorted(counts)
