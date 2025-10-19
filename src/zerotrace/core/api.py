import httpx
from typing import Optional, List

BASE_URL = "https://zerotrace-production.up.railway.app"

class API:
    @staticmethod
    def get_user_public_key(hash_public: str, addr: str) -> Optional[dict]:
        try:
            r = httpx.get(f"{addr}/user/{hash_public}")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError:
            return None

    @staticmethod
    def send_message(
        current_node_identifier: str,
        recipient_identifier: str,
        shared_secret_ciphertext:str,
        crypted_msg: str,
        nonce_msg: str,
        signature: str,
        addr: str
    ) -> bool:

        try:
            r = httpx.post(
                f"{addr}/send",
                json={
                    "current_node_identifier": current_node_identifier,
                    "recipient_identifier": recipient_identifier,
                    "shared_secret_ciphertext": shared_secret_ciphertext,
                    "message_ciphertext": crypted_msg,
                    "nonce": nonce_msg,
                    "signature": signature
                },
            )
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to send message: {e}")
            return False

    @staticmethod
    def get_messages(public_key: str, last_timestamp: int) -> List[dict]:
        try:
            r = httpx.get(
                f"{BASE_URL}/messages/{public_key}", params={"last": last_timestamp}
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []
    
    @staticmethod
    def get_dialog_messages(dialog_hash: str, last_timestamp: float) -> List[dict]:
        try:
            r = httpx.get(
                f"{BASE_URL}/dialog/{dialog_hash}", params={"last": last_timestamp}
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []
    
    @staticmethod
    def get_dialogs(public_key) -> List[dict]:
        try:
            r = httpx.get(
                f"{BASE_URL}/dialogs/{public_key}"
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []
    def search_user(self, query: str) -> List[dict]:
        try:
            r = httpx.get(
                f"{BASE_URL}/users/{query}"
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []