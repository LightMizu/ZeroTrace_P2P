from fastapi import FastAPI
from zerotrace.core.scheme import MessageModel
from zerotrace.core.messenger_core import SecureMessenger
from zerotrace.core.database import Database
import httpx 
def add_routers(app: FastAPI, messanger: SecureMessenger) -> FastAPI:
    database = Database()
    @app.post("/send")
    async def send_message(message: MessageModel):
        if await database.get_entry(message.signature):
            return {"status": "OK"}
        await database.add_entry(message.signature)
        if message.recipient_identifier == messanger.identifier:
            msg = messanger.decrypt_message(message.model_dump())
            if database.get_contact(msg["sender_id"]) is None:
                await database.add_contact(identifier=msg["sender_id"], kem_public_key=msg["kem_public_key"], sign_public_key=msg["signature_public_key"], addr=msg["sender_dest"])
            await database.add_message(content_b64=msg["message"],timestamp=msg["timestamp"],sender_id=msg["sender_id"])
            return {"status": "OK"}
        forward_message = message.model_copy()
        if database.get_contact(message.recipient_identifier):
            await database.add_forward_message(recipient_identifier=message.recipient_identifier, shared_secret_ciphertext=message.shared_secret_ciphertext, message_ciphertext=message.message_ciphertext, nonce=message.nonce, signature=message.signature)
            forward_message.max_recursive_contact -= 1
        forward_message.current_node_identifier = messanger.identifier
        # Decrement TTL
        forward_message.ttl -= 1
        if forward_message.ttl  > 0 and forward_message.max_recursive_contact > 0:
            contacts = await database.list_contacts()
            async with httpx.AsyncClient() as client:
                for contact in contacts:
                    # Skip sending back to the sender
                    if contact["identifier"] == message.current_node_identifier:
                        continue
                    try:
                        await client.post(contact["addr"] + "/send", json=forward_message.model_dump())
                    except httpx.HTTPError:
                        # Could log failed attempt
                        pass
    return app