import pytest
from src.kademlia.kademlia.routing import RoutingTable, KBucket
from src.kademlia.kademlia.utils import Node, random_node_id


@pytest.fixture
def routing_table():
    nid = random_node_id()
    return RoutingTable(None, ksize=20, node=Node(nid))


def test_routing_add_and_find():
    nid = random_node_id()
    rt = RoutingTable(None, ksize=3, node=Node(nid))
    # add a few nodes
    nodes = [Node(random_node_id(), '127.0.0.1', p) for p in (1000, 1001, 1002, 1003)]
    for n in nodes:
        rt.add_contact(n)
    # find neighbors for a random key
    target = Node(random_node_id())
    neighbors = rt.find_neighbors(target, k=3)
    assert isinstance(neighbors, list)
    assert len(neighbors) <= 3


def test_routing_is_new_node(routing_table):
    """Test detection of new nodes."""
    node = Node(random_node_id(), '127.0.0.1', 1000)
    assert routing_table.is_new_node(node) is True
    routing_table.add_contact(node)
    assert routing_table.is_new_node(node) is False


def test_routing_split_bucket(routing_table):
    """Test bucket splitting when it becomes full."""
    # Fill up the bucket
    nodes = []
    for i in range(20):
        node = Node(random_node_id(), '127.0.0.1', 2000 + i)
        nodes.append(node)
        routing_table.add_contact(node)
    
    # Add one more node to trigger split
    extra_node = Node(random_node_id(), '127.0.0.1', 2050)
    routing_table.add_contact(extra_node)
    
    # Check that we have more than one bucket
    assert len(routing_table.buckets) > 1


def test_routing_remove_contact(routing_table):
    """Test removing a contact."""
    node = Node(random_node_id(), '127.0.0.1', 3000)
    routing_table.add_contact(node)
    assert not routing_table.is_new_node(node)
    
    routing_table.remove_contact(node)
    assert routing_table.is_new_node(node)


def test_routing_find_neighbors_same_bucket():
    """Test finding neighbors when they're in the same bucket."""
    nid = random_node_id()
    rt = RoutingTable(None, ksize=5, node=Node(nid))
    
    nodes = []
    for i in range(5):
        node = Node(random_node_id(), '127.0.0.1', 5000 + i)
        nodes.append(node)
        rt.add_contact(node)
    
    target = nodes[0]
    neighbors = rt.find_neighbors(target)
    assert len(neighbors) == 4  # All nodes except target


def test_kbucket_properties():
    """Test KBucket basic properties."""
    bucket = KBucket(0, 100, 3)
    assert bucket.range == (0, 100)
    assert bucket.ksize == 3
    
    node = Node(random_node_id(), '127.0.0.1', 6000)
    bucket.add_node(node)
    assert len(bucket.nodes) == 1
    
    nodes = bucket.get_nodes()
    assert len(nodes) == 1
    assert nodes[0].id == node.id


def test_kbucket_replacement_nodes():
    """Test KBucket replacement nodes functionality."""
    bucket = KBucket(0, 100, 2)  # Small ksize to test replacement
    
    # Add nodes up to ksize
    node1 = Node(random_node_id(), '127.0.0.1', 7000)
    node2 = Node(random_node_id(), '127.0.0.1', 7001)
    bucket.add_node(node1)
    bucket.add_node(node2)
    
    # Try to add another node - should go to replacement nodes
    node3 = Node(random_node_id(), '127.0.0.1', 7002)
    bucket.add_node(node3)
    
    assert len(bucket.nodes) == 2
    assert len(bucket.replacement_nodes) == 1
    
    # Remove a node and check if replacement is used
    bucket.remove_node(node1)
    assert len(bucket.nodes) == 2
    assert len(bucket.replacement_nodes) == 0
