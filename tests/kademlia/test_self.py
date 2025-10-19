import pytest
from src.zerotrace.kademlia.client import Client
from src.zerotrace.kademlia.routing import KBucket, RoutingTable
from src.zerotrace.kademlia.server import Server
from src.zerotrace.kademlia.utils import digest
import asyncio
import random
import os

class TestSelfNode:
    @pytest.fixture
    async def server(self):
        """Create a test server instance"""
        server = Server()
        await server.listen(8468)
        yield server
        await server.stop()

    @pytest.fixture
    def routing_table(self):
        """Create a test routing table"""
        return RoutingTable(digest(random.getrandbits(255)))

    @pytest.mark.asyncio
    async def test_server_start_stop(self, server):
        """Test basic server start and stop functionality"""
        assert server.protocol is not None
        assert server.protocol.transport is not None
        await server.stop()
        assert server.protocol.transport is None

    @pytest.mark.asyncio
    async def test_node_ping(self, server):
        """Test node ping functionality"""
        client = Client()
        await client.listen(8469)
        result = await client.ping(('127.0.0.1', 8468))
        assert result is True
        await client.stop()

    @pytest.mark.asyncio
    async def test_node_store_find(self, server):
        """Test storing and finding a value"""
        client = Client()
        await client.listen(8470)
        
        # Store a value
        key = digest('test_key')
        value = b'test_value'
        await client.set(key, value)
        
        # Find the value
        result = await client.get(key)
        assert result == value
        await client.stop()

    @pytest.mark.asyncio
    async def test_routing_table(self, routing_table):
        """Test routing table functionality"""
        # Create some test nodes
        test_nodes = [(digest(random.getrandbits(255)), ('127.0.0.1', random.randint(8000, 9000))) 
                      for _ in range(5)]
        
        # Add nodes to routing table
        for node_id, address in test_nodes:
            routing_table.add_contact(node_id, address)
        
        # Test finding closest nodes
        target_key = digest(random.getrandbits(255))
        closest = routing_table.find_closest_nodes(target_key)
        assert len(closest) > 0

    @pytest.mark.asyncio
    async def test_kbucket_functionality(self):
        """Test KBucket operations"""
        k = 20  # k-bucket size
        bucket = KBucket(0, 2**160, k)
        
        # Add nodes to bucket
        for i in range(k):
            node_id = digest(random.getrandbits(255))
            bucket.add_contact(node_id, ('127.0.0.1', 8000 + i))
        
        assert len(bucket) == k
        # Try adding one more node - should fail as bucket is full
        extra_node = digest(random.getrandbits(255))
        bucket.add_contact(extra_node, ('127.0.0.1', 9000))
        assert len(bucket) == k  # Size should remain the same

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, server):
        """Test concurrent operations on the network"""
        clients = []
        try:
            # Create multiple clients
            for i in range(3):
                client = Client()
                await client.listen(8471 + i)
                clients.append(client)

            # Perform concurrent operations
            tasks = []
            for client in clients:
                key = digest(f'test_key_{random.randint(1, 1000)}'.encode())
                value = f'test_value_{random.randint(1, 1000)}'.encode()
                tasks.append(asyncio.create_task(client.set(key, value)))
                tasks.append(asyncio.create_task(client.get(key)))

            # Wait for all operations to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            assert all(not isinstance(r, Exception) for r in results)

        finally:
            # Cleanup
            for client in clients:
                await client.stop()

    @pytest.mark.asyncio
    async def test_node_bootstrap(self, server):
        """Test node bootstrapping process"""
        client = Client()
        await client.listen(8474)
        
        # Bootstrap the client with the server
        result = await client.bootstrap([('127.0.0.1', 8468)])
        assert result is True
        
        # Verify the routing table has been populated
        assert len(client.protocol.router.buckets[0]) > 0
        await client.stop()

    @pytest.mark.asyncio
    async def test_network_partition(self, server):
        """Test behavior during network partitions"""
        client1 = Client()
        client2 = Client()
        
        await client1.listen(8475)
        await client2.listen(8476)
        
        # Store value before simulating partition
        key = digest('partition_test')
        value = b'test_value'
        await client1.set(key, value)
        
        # Simulate partition by stopping client2
        await client2.stop()
        
        # Try to get value during partition
        result = await client1.get(key)
        assert result == value
        
        await client1.stop()

    @pytest.mark.asyncio
    async def test_large_data_transfer(self, server):
        """Test handling of large data transfers"""
        client = Client()
        await client.listen(8477)
        
        # Create large test data (1MB)
        large_data = os.urandom(1024 * 1024)
        key = digest('large_data_test')
        
        # Store and retrieve large data
        await client.set(key, large_data)
        result = await client.get(key)
        
        assert result == large_data
        await client.stop()