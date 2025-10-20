import pytest
import httpx
from types import SimpleNamespace
from httpx import ASGITransport
from fastapi.testclient import TestClient

from src.zerotrace.kademlia.client import DHTClient
from src.zerotrace.kademlia.server import create_app
import src.zerotrace.kademlia.client as client_module

@pytest.mark.asyncio 
async def test_find_value_recursive_integration_local_store(tmp_path, monkeypatch):
    """
    Integration: store a value via the app's /store endpoint, then use DHTClient.find_value_recursive
    with an AsyncClient bound to the ASGI app so that calls are handled in-process.
    """
    db_path = str(tmp_path / "int_node.db")
    app = create_app(port=9000, db_path=db_path)

    # Use TestClient to perform the store operation synchronously 
    tc = TestClient(app)

    key = "6b6579"   # "key"
    value = "76616c"  # "val"
    node_id = "01" * 20

    resp = tc.post("/store", json={"node_id": node_id, "key": key, "value": value})
    assert resp.status_code == 200

    # Create a DHTClient and replace its internal _client with an httpx.AsyncClient
    d = DHTClient(host="127.0.0.1", port=9000)
    asgi_client = httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    )
    d._client = asgi_client

    # Monkeypatch the module-level httpx.AsyncClient 
    def async_client_factory(*args, **kwargs):
        base_url = kwargs.get("base_url") or (args[0] if args else None) or "http://test"
        return httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url=base_url
        )

    monkeypatch.setattr(client_module, "httpx", SimpleNamespace(AsyncClient=async_client_factory))

    try:
        res = await d.find_value_recursive(node_id=node_id, key=bytes.fromhex(key))
        assert res == bytes.fromhex(value)
    finally:
        await asgi_client.aclose()
        await d.close()
        tc.close()