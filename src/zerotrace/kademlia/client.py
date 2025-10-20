import httpx
from typing import Optional, Union, Set


class DHTClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.base_url = f"http://{host}:{port}"
        self._client = httpx.AsyncClient(base_url=self.base_url)

    async def _post(self, path: str, json: dict):
        r = await self._client.post(path, json=json, timeout=10.0)
        r.raise_for_status()
        return r.json()

    async def get_id(self) -> str:
        r = await self._client.get("/id")
        r.raise_for_status()
        return r.json()["id"]

    async def bootstrap(self, target_host: str, target_port: int, symmetric: bool = True) -> bool:
        """Bootstrap this node to a known node in the DHT network.
        
        Args:
            target_host: IP address or hostname of the bootstrap node
            target_port: Port of the bootstrap node
            symmetric: If True, also tell the target to add us (bidirectional)
            
        Returns:
            True if bootstrap succeeded, False otherwise
        """
        try:
            # Get our own node ID and connection info
            our_node_id = await self.get_id()
            
            # Parse our own host and port from base_url
            # base_url format: http://host:port
            our_url_parts = self.base_url.replace('http://', '').replace('https://', '').split(':')
            our_host = our_url_parts[0] if len(our_url_parts) > 0 else '127.0.0.1'
            our_port = int(our_url_parts[1]) if len(our_url_parts) > 1 else 8000
            
            # Get target node's ID
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://{target_host}:{target_port}/id", timeout=5.0)
                resp.raise_for_status()
                target_node_id = resp.json()["id"]
            
            # Send bootstrap request to target (we want to add them)
            payload = {
                "node_id": target_node_id,
                "ip": target_host,
                "port": target_port,
                "key": "",
                "value": ""
            }
            result = await self._post("/bootstrap", json=payload)
            
            if not result.get("ok", False):
                return False
            
            # Symmetric bootstrap: ask target to add us too
            if symmetric:
                try:
                    async with httpx.AsyncClient() as client:
                        symmetric_payload = {
                            "node_id": our_node_id,
                            "ip": our_host,
                            "port": our_port,
                            "key": "",
                            "value": ""
                        }
                        resp = await client.post(
                            f"http://{target_host}:{target_port}/bootstrap",
                            json=symmetric_payload,
                            timeout=5.0
                        )
                        resp.raise_for_status()
                        # Both nodes now know each other
                except Exception as e:
                    # Log but don't fail - we still added them to our routing table
                    print(f"Symmetric bootstrap warning: {e}")
            
            return True
            
        except Exception as e:
            print(f"Bootstrap failed: {e}")
            return False

    async def find_value_recursive(
        self,
        node_id: str,
        key: Union[str, bytes],
        visited: Optional[Set[str]] = None,
        depth: int = 0,
        max_depth: int = 5,
    ) -> Optional[bytes]:
        """
        Рекурсивный поиск значения в DHT — если значение не найдено локально,
        запрашивает ближайшие узлы и идёт дальше.
        """
        if isinstance(key, bytes):
            key_hex = key.hex()
        else:
            key_hex = key

        if visited is None:
            visited = set()

        visited.add(self.base_url)

        # делаем локальный запрос
        payload = {"node_id": node_id, "key": key_hex, "ip": "127.0.0.1", "port": 0}
        result = await self._post("/find_value", json=payload)

        if "value" in result:
            try:
                return bytes.fromhex(result["value"])
            except Exception:
                return result["value"]

        # если вернулись соседи — пробуем к ним
        neighbors = result.get("nodes", [])
        for nid, ip, port in neighbors:
            url = f"http://{ip}:{port}"
            if url in visited:
                continue
            try:
                async with httpx.AsyncClient(base_url=url) as client:
                    payload = {"node_id": node_id, "key": key_hex, "ip": ip, "port": port}
                    res = await client.post("/find_value", json=payload, timeout=5.0)
                    data = res.json()
                    if "value" in data:
                        try:
                            return bytes.fromhex(data["value"])
                        except Exception:
                            return data["value"]
                    if depth < max_depth and "nodes" in data:
                        next_client = DHTClient(ip, port)
                        val = await next_client.find_value_recursive(
                            node_id, key_hex, visited=visited, depth=depth + 1
                        )
                        await next_client.close()
                        if val:
                            return val
            except Exception:
                continue

        return None

    async def close(self):
        await self._client.aclose()
