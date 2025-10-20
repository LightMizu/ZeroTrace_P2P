import json
from typing import Tuple
from typing import Dict
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hmac, hashes

from zerotrace.core.symmetric.crypto import SymmetricCrypto
from zerotrace.core.post_quantum.crypto import PostQuantumCrypto
from zerotrace.core.post_quantum.sign import PostQuantumSignature
from zerotrace.core.utils import (
    CryptoUtils,
    b64_dec,
    b64_enc,
    key_pair_id_base64url,
)
from zerotrace.core.models import KeyBundle


class SecureMessenger:
    kem_public_key: bytes
    __kem_private_key: bytes
    signature_public_key: bytes
    __signature_private_key: bytes
    identifier: str
    ip: str

    def __init__(self, ip):
        self.__quantum = PostQuantumCrypto()
        self.__symmetric = SymmetricCrypto()
        self.ip = ip
        self.__signature = PostQuantumSignature()


    def generate_keys(self) -> Tuple[bytes, bytes]:
        kem_private_key, kem_public_key, signature_private_key, signature_public_key = (
            self.__quantum.generate_key_pair()
        )
        self.kem_public_key = kem_public_key
        self.__kem_private_key = kem_private_key
        self.__signature_private_key = signature_private_key
        self.signature_public_key = signature_public_key
        self.identifier = key_pair_id_base64url(kem_pub=self.kem_public_key, sig_pub=self.signature_public_key)
        return kem_public_key, signature_public_key

    def save_keys(self, password: bytes) -> KeyBundle:
        salt = os.urandom(16)
        aes_key = CryptoUtils.derive_key_scrypt(password, salt)
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)

        encrypted_kem_private = aesgcm.encrypt(nonce, self.__kem_private_key, None)
        encrypted_signature_private = aesgcm.encrypt(
            nonce, self.__signature_private_key, None
        )

        # HMAC для быстрой проверки пароля
        h = hmac.HMAC(aes_key, hashes.SHA256())
        h.update(b"keycheck")
        keycheck = h.finalize()

        return {
            "salt": b64_enc(salt),
            "nonce": b64_enc(nonce),
            "public_keys": {
                "kem.public": b64_enc(self.kem_public_key),
                "sig.public": b64_enc(self.signature_public_key),
            },
            "encrypted_keys": {
                "kem.private": b64_enc(encrypted_kem_private),
                "sig.private": b64_enc(encrypted_signature_private),
            },
            "keycheck": b64_enc(keycheck),
        }

    def load_keys(self, data: KeyBundle, password: bytes) -> bool:
        salt = b64_dec(data["salt"])
        nonce = b64_dec(data["nonce"])

        kem_public = b64_dec(data["public_keys"]["kem.public"])
        sign_public = b64_dec(data["public_keys"]["sig.public"])
        encrypted_keys = data["encrypted_keys"]
        keycheck_saved = b64_dec(data["keycheck"])
        aes_key = CryptoUtils.derive_key_scrypt(password, salt)
        # Проверка HMAC — быстрая проверка пароля
        h = hmac.HMAC(aes_key, hashes.SHA256())
        h.update(b"keycheck")
        try:
            h.verify(keycheck_saved)
        except Exception:
            print("Wrong Password")
            return False

        aesgcm = AESGCM(aes_key)

        kem_private_key = aesgcm.decrypt(
            nonce, b64_dec(encrypted_keys["kem.private"]), None
        )
        signature_private_key = aesgcm.decrypt(
            nonce, b64_dec(encrypted_keys["sig.private"]), None
        )

        self.kem_public_key = kem_public
        self.__kem_private_key = kem_private_key
        self.signature_public_key = sign_public
        self.__signature_private_key = signature_private_key
        self.identifier = key_pair_id_base64url(kem_pub=self.kem_public_key, sig_pub=self.signature_public_key)
        return True

    def encrypt_message(
        self, recipient_identifier:str, recipient_kem_public_key: bytes, message: bytes, timestamp: float
    ) -> Dict:
        #Шаг 0: Подготовка сообщения
        message_payload = json.dumps(
                {
                    "ip":self.ip,
                    "message": b64_enc(message),
                    "sender_id": key_pair_id_base64url(
                        kem_pub=self.kem_public_key,
                        sig_pub=self.signature_public_key
                    ),
                    "timestamp": timestamp,
                    "signature_public_key": b64_enc(self.signature_public_key),
                    "kem_public_key": b64_enc(self.kem_public_key),
                }
            ).encode()

        # Шаг 1: Создание общего секрета

        shared_secret, shared_secret_kem_ciphertext = self.__quantum.encapsulate(
            recipient_kem_public_key
        )

        # Шаг 2: Шифрование сообщения
        msg_ciphertext, msg_nonce = self.__symmetric.encrypt(
            message_payload,
            CryptoUtils.derive_key_hkdf(shared_secret),
        )
        # Шаг 3: Подписание сообщения
        signature = self.__signature.sign(message_payload, self.__signature_private_key)


        return {
            "recipient_identifier":recipient_identifier,
            "shared_secret_ciphertext":b64_enc(shared_secret_kem_ciphertext),
            "message_ciphertext":b64_enc(msg_ciphertext),
            "nonce":b64_enc(msg_nonce),
            "signature":b64_enc(signature),
        }

    def decrypt_message(self, message: Dict[str,str]) -> Dict[str,str]:

        #message
        # "current_node_identifier": current_node_identifier,
        # "recipient_identifier": recipient_identifier,
        # "shared_secret_ciphertext": shared_secret_ciphertext,
        # "message_ciphertext": crypted_msg,
        # "nonce": nonce_msg,
        # "signature": signature

        #decrypted message
        # "message": b64_enc(message)
        # "sender_id": key_pair_id_base64url(kem_pub=self.kem_public_key,sig_pub=self.signature_public_key)
        # "signature_public_key": b64_enc(self.signature_public_key)
        # "timestamp": timestamp,
        # "kem_public_key": b64_enc(self.kem_public_key)

        shared_secret = self.__quantum.decapsulate(
            self.__kem_private_key, b64_dec(message["shared_secret_ciphertext"])
        )

        # Шаг 2: Дешифровка сообщения
        data: bytes = self.__symmetric.decrypt(
                b64_dec(message["message_ciphertext"]),
                CryptoUtils.derive_key_hkdf(shared_secret),
                b64_dec(message["nonce"]),
            )
        # Шаг 3: Проверка хеша публичных ключей

        message_payload: Dict[str,str] = json.loads(data.decode())

        # Шаг 4: Проверка подписи
        if not self.__signature.verify(
            data,
            b64_dec(message["signature"]),
            b64_dec(message_payload["signature_public_key"])
        ):
            return {"result": "Signature invalid"}

        #Щаг 5: Сверяем хэш
        calculated_id = key_pair_id_base64url(sig_pub=b64_dec(message_payload["signature_public_key"]),kem_pub=b64_dec(message_payload["kem_public_key"]))
        if calculated_id != message_payload["sender_id"]:
            return {"result": "Hash invalid"}
        decrypted_message = {
            "sender_id": calculated_id,
            "message": b64_dec(message_payload["message"]),
            "signature_public_key": message_payload["signature_public_key"],
            "sender_dest": message_payload["ip"],
            "kem_public_key": message_payload["kem_public_key"],
            "timestamp": message_payload["timestamp"]
        } 
        return decrypted_message
