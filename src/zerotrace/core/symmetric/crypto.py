from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from typing import Tuple
import os

class SymmetricCrypto:
    @staticmethod
    def encrypt(data: bytes, key: bytes) -> Tuple[bytes, bytes]:
        """
        Шифрование AES-256-GCM
        Возвращает (ciphertext, nonce, auth_tag)
        """
        aes = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aes.encrypt(nonce, data, None)
        return ciphertext, nonce

    @staticmethod
    def decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
        """
        Дешифрование с проверкой подлинности
        """
        aes = AESGCM(key)
        try:
            return aes.decrypt(nonce, ciphertext, None)
        except InvalidTag:
            raise ValueError("Ошибка аутентификации данных")

