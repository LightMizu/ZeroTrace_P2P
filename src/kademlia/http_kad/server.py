from fastapi import FastAPI
from pydantic import BaseModel

from .utils import Node, random_node_id, digest
from .persistent_storage import SQLiteStorage
from .routing import RoutingTable


class PingRequest(BaseModel):
    node_id: str
    ip: str = "127.0.0.1"
    port: int = 0


class StoreRequest(BaseModel):
    node_id: str
    ip: str = "127.0.0.1"
    port: int = 0
    key: str
    value: str


class FindNodeRequest(BaseModel):
    node_id: str
    ip: str = "127.0.0.1"
    port: int = 0
    key: str


class FindValueRequest(BaseModel):
    node_id: str
    ip: str = "127.0.0.1"
    port: int = 0
    key: str


class Server:
    def __init__(self, port: int, ksize: int = 20, alpha: int = 3, db_path: str = None):
        self.ksize = ksize
        self.alpha = alpha
        # Default to a memory-backed sqlite URI to avoid creating files on disk when
        # no explicit db_path is provided. Use port in the name to keep per-server DBs
        # separate while still being in-memory.
        if db_path:
            db_name = db_path
        else:
            db_name = f"file:kademlia_{port}?mode=memory&cache=shared"
        self.storage = SQLiteStorage(db_name)
        self.node = Node(random_node_id(), "127.0.0.1", port)
        self.protocol = None
        self.routing = RoutingTable(self, self.ksize, self.node)
        self.port = port
        self._load_saved_nodes()

    def _load_saved_nodes(self):
        """Load previously saved nodes from storage."""
        nodes = self.storage.get_known_nodes(max_age=self.storage.ttl)
        for node in nodes:
            if node.id != self.node.id:  # Don't add ourselves
                self.routing.add_contact(node)

    def welcome_if_new(self, node: Node):
        if not self.routing.is_new_node(node):
            return
        self.routing.add_contact(node)
        # Store the node in persistent storage
        self.storage.store_node(node)

    async def call_store(self, node: Node, key: bytes, value: bytes) -> bool:
        # Try to replicate to another in-process server instance (tests)
        target = _app_cache.get(node.port)
        if not target:
            return False
        try:
            target.storage[key] = value
            return True
        except Exception:
            return False

    async def set_digest(self, dkey: bytes, value: bytes) -> bool:
        """Store the digest on the k closest nodes (replication).

        Returns True if at least one remote store succeeded.
        """
        node = Node(dkey)
        nearest = self.routing.find_neighbors(node, k=self.ksize)
        results = []
        # store locally if appropriate
        if nearest:
            biggest = max([n.distance_to(node) for n in nearest])
            if self.node.distance_to(node) < biggest:
                self.storage[dkey] = value
        else:
            # no neighbors known: store locally
            self.storage[dkey] = value

        for n in nearest:
            ok = await self.call_store(n, dkey, value)
            results.append(ok)
        return any(results)


_app_cache = {}


def create_app(port: int = 8000) -> FastAPI:
    app = FastAPI()
    svr = Server(port)
    _app_cache[port] = svr

    @app.get("/id")
    def get_id():
        return {"id": svr.node.id.hex()}

    @app.post("/ping")
    async def ping(req: PingRequest):
        try:
            nid = bytes.fromhex(req.node_id)
        except Exception:
            nid = req.node_id.encode()
        src = Node(nid, "unknown", 0)
        svr.welcome_if_new(src)
        return {"id": svr.node.id.hex()}

    @app.post("/store")
    async def store(req: StoreRequest):
        try:
            nid = bytes.fromhex(req.node_id)
        except Exception:
            nid = req.node_id.encode()
        src = Node(nid, "unknown", 0)
        svr.welcome_if_new(src)
        try:
            key = bytes.fromhex(req.key)
        except Exception:
            key = req.key.encode()
        try:
            value = bytes.fromhex(req.value)
        except Exception:
            value = req.value.encode()
        svr.storage[key] = value
        return {"ok": True}

    @app.post("/set")
    async def set_value(req: StoreRequest):
        # store by digest and replicate to k nearest
        try:
            key = bytes.fromhex(req.key)
        except Exception:
            key = req.key.encode()
        try:
            value = bytes.fromhex(req.value)
        except Exception:
            value = req.value.encode()
        ok = await svr.set_digest(key, value)
        return {"ok": ok}

    @app.post("/bootstrap")
    async def bootstrap(req: StoreRequest):
        # simple bootstrap: add provided node as contact
        try:
            nid = bytes.fromhex(req.node_id)
        except Exception:
            nid = req.node_id.encode()
        src = Node(nid, req.ip, req.port)
        svr.welcome_if_new(src)
        return {"ok": True}

    @app.post("/find_node")
    async def find_node(req: FindNodeRequest):
        try:
            nid = bytes.fromhex(req.node_id)
        except Exception:
            nid = req.node_id.encode()
        src = Node(nid, "unknown", 0)
        svr.welcome_if_new(src)
        try:
            key = bytes.fromhex(req.key)
        except Exception:
            key = req.key.encode()
        node = Node(key)
        neighbors = svr.routing.find_neighbors(node)
        return {"nodes": [(n.id.hex(), n.ip, n.port) for n in neighbors]}

    @app.post("/find_value")
    async def find_value(req: FindValueRequest):
        try:
            nid = bytes.fromhex(req.node_id)
        except Exception:
            nid = req.node_id.encode()
        src = Node(nid, "unknown", 0)
        svr.welcome_if_new(src)
        try:
            key = bytes.fromhex(req.key)
        except Exception:
            key = req.key.encode()
        val = svr.storage.get(key, None)
        if val is not None:
            try:
                return {"value": val.hex()}
            except Exception:
                return {"value": str(val)}
        node = Node(key)
        neighbors = svr.routing.find_neighbors(node)
        return {"nodes": [(n.id.hex(), n.ip, n.port) for n in neighbors]}

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app(8000)
    uvicorn.run(app, host="0.0.0.0", port=8000)
