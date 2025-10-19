from pydantic import BaseModel
class MessageModel(BaseModel):
    current_node_identifier: str
    recipient_identifier: str
    shared_secret_ciphertext: str
    message_ciphertext: str
    nonce: str
    signature: str
    ttl: int
    max_recursive_contact: int