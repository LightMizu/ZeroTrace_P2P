from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives import hashes
from enum import Enum
import base64
import binascii
import hashlib

class CryptoUtils:
    @staticmethod
    def derive_key_hkdf(key_bytes: bytes) -> bytes:
        """
        Генерация ключа из общего секрета через HKDF
        """
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"aes_key_derivation",
        ).derive(key_bytes)
    @staticmethod
    def derive_key_scrypt(password: bytes, salt: bytes, length: int = 32) -> bytes:
        kdf = Scrypt(salt=salt, length=length, n=2**14, r=8, p=1)
        return kdf.derive(password)

def b64_enc(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode()

def b64_dec(data_str: str) -> bytes:
    return base64.urlsafe_b64decode(data_str)

def _len_prefixed(b: bytes) -> bytes:
    # простая каноническая упаковка: 4-байт big-endian length + data
    return len(b).to_bytes(4, "big") + b

def key_pair_id_base64url(kem_pub: bytes, sig_pub: bytes, *,
                        version: bytes = b"KEM-SIG-v1:",
                        hash_name: str = "sha256") -> str:
    """
    Возвращает URL-safe base64 (без '=') идентификатор пары публичных ключей.

    - kem_pub, sig_pub: raw bytes публичных ключей (SPKI / raw)
    - version: префикс/версия, чтобы избежать конфликтов при смене схемы
    - hash_name: имя хэш-функции (sha256, blake2b, ...)
    """
    h = hashlib.new(hash_name)
    h.update(version)
    h.update(_len_prefixed(kem_pub))
    h.update(_len_prefixed(sig_pub))
    digest = h.digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def key_pair_id_hex(kem_pub: bytes, sig_pub: bytes, *,
                    version: bytes = b"KEM-SIG-v1:",
                    hash_name: str = "sha256",
                    truncate_bytes: int | None = None) -> str:
    """То же в hex-строке (удобно для логов)."""
    
    h = hashlib.new(hash_name)
    h.update(version)
    h.update(_len_prefixed(kem_pub))
    h.update(_len_prefixed(sig_pub))
    digest = h.digest()
    if truncate_bytes is not None:
        digest = digest[:truncate_bytes]
    return binascii.hexlify(digest).decode("ascii")

class MessageType(Enum):
    TEXT = 0
    FILE = 1
    IMG = 2
    LOAD = 5