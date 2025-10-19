import httpx
from typing import Optional, List, Tuple, Union, Set


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
