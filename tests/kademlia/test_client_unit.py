import pytest
from types import SimpleNamespace

# Import the class to test (package import)
from src.zerotrace.kademlia.client import DHTClient
import src.zerotrace.kademlia.client as client_module


@pytest.mark.asyncio
async def test_find_value_recursive_returns_local_value():
    """If /find_value on the local node returns a value, it should be returned as bytes."""
    d = DHTClient(host="127.0.0.1", port=8000)

    async def fake_post(path: str, json: dict):
        # emulate response with hex-encoded value for b"local-val"
        return {"value": b"local-val".hex()}

    # replace _post with the fake
    d._post = fake_post

    try:
        res = await d.find_value_recursive(node_id="01" * 20, key=b"ignored")
        assert res == b"local-val"
    finally:
        await d.close()


@pytest.mark.asyncio
async def test_find_value_recursive_follows_neighbor_and_finds_value(monkeypatch):
    """If local node returns neighbors, the client should contact neighbor and return the neighbor's value."""
    d = DHTClient(host="127.0.0.1", port=8000)

    async def fake_local_post(path: str, json: dict):
        # local /find_value returns a single neighbor (ip,port)
        return {"nodes": [("n1", "127.0.0.1", 9001)]}

    d._post = fake_local_post

    # Fake response object returned by AsyncClient.post()
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    # Fake AsyncClient used in the neighbor branch inside find_value_recursive
    class FakeAsyncClient:
        def __init__(self, base_url=None, **kwargs):
            self.base_url = base_url

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, path, json=None, timeout=None):
            # neighbor returns the value for b"neighbor-val"
            return FakeResponse({"value": b"neighbor-val".hex()})

        async def aclose(self):
            return None

    # Monkeypatch httpx.AsyncClient used inside the module to our FakeAsyncClient
    monkeypatch.setattr(client_module, "httpx", SimpleNamespace(AsyncClient=FakeAsyncClient))

    try:
        res = await d.find_value_recursive(node_id="02" * 20, key=b"ignored")
        assert res == b"neighbor-val"
    finally:
        await d.close()