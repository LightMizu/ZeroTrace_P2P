from fastapi import FastAPI
from zerotrace.core.scheme import MessageModel
from zerotrace.core.messenger_core import SecureMessenger
from zerotrace.core.database import ContactManager, MessageManager, ForwardMessageManager

def add_routers(app: FastAPI, messanger: SecureMessenger) -> FastAPI:
    contacts_manager = ContactManager()
    message_manager = MessageManager()
    forward_message_manager = ForwardMessageManager()
    @app.post("/send")
    async def send_message(message: MessageModel):
        #Check message seen in history. Check by signature
        if message.recipient_identifier == messanger.identifier:
            msg = messanger.decrypt_message(message.model_dump())
            if contacts_manager.get_contact(msg["sender_id"]) is None:
                await contacts_manager.add_contact(identifier=msg["sender_id"], kem_public_key=msg["kem_public_key"], sign_public_key=msg["signature_public_key"], addr="")
            #Store local
            #If new contact add to contact
            return
        if contacts_manager.get_contact(message.recipient_identifier):
            ...
            #Store message in database
            #Forward other contacts
        else:
            ...
            #Forward other contacts
    return app