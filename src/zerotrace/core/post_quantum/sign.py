from oqs import Signature
from typing import Tuple

class PostQuantumSignature:
    ALGORITHM = "Dilithium2"  # Можно заменить на другой вариант SPHINCS+

    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Генерация ключевой пары SPHINCS+ с использованием pyOQS.
        Возвращает (public_key, private_key) в hex.
        """
        with Signature(PostQuantumSignature.ALGORITHM) as signer:
            public_key = signer.generate_keypair()
            secret_key = signer.export_secret_key()
            return public_key, secret_key

    @staticmethod
    def sign(message: bytes, private_key: bytes) -> bytes:
        """
        Подписывает сообщение с использованием SPHINCS+.
        Возвращает подпись в hex.
        """
        with Signature(PostQuantumSignature.ALGORITHM, private_key) as signer:
            signature = signer.sign(message)
            return signature

    @staticmethod
    def verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
        """
        Проверяет подпись с использованием SPHINCS+.
        """
        with Signature(PostQuantumSignature.ALGORITHM) as verifier:
            return verifier.verify(message, signature, public_key)




