import hashlib
import secrets
from hashlib import sha1

def digest(data: bytes) -> bytes:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha1(data).digest()


class Node:
    def __init__(self, node_id: bytes, ip: str = "127.0.0.1", port: int = 0):
        self.id = node_id
        self.ip = ip
        self.port = port
        self.long_id = int.from_bytes(node_id, byteorder="big")

    def distance_to(self, other: 'Node') -> int:
        return self.long_id ^ other.long_id

    def same_home_as(self, other: 'Node') -> bool:
        return self.ip == other.ip and self.port == other.port

    def __repr__(self):
        return f"Node({self.id.hex()[:8]}..., {self.ip}:{self.port})"


def random_node_id() -> bytes:
    """
    Генерирует криптографически безопасный 20-байтный идентификатор узла.
    """
    random_bytes = secrets.token_bytes(20)  # 20 случайных байт
    return sha1(random_bytes).digest() 
