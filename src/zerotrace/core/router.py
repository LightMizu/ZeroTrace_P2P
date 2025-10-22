from functools import total_ordering
from fastapi import FastAPI
from src.zerotrace.core.scheme import MessageModel
from src.zerotrace.core.messenger_core import SecureMessenger
from src.zerotrace.core.database import Database
from src.zerotrace.core.http_client import create_http_client
from src.zerotrace.kademlia.logging import init_logger, default_logger
import asyncio
import httpx
import logging
import random

# Setup Python logging for debug/trace
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zerotrace_router.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Removed global database instance - will be passed as parameter
async def forward_message_task(forward_message, message, database):
    """Фоновая задача для пересылки сообщения"""
    logger.info(f"[FORWARD_TASK] Starting forward task for message to {message.recipient_identifier}")
    logger.info(f"[FORWARD_TASK] TTL: {forward_message.ttl}, Max recursive: {forward_message.max_recursive_contact}")
    
    if forward_message.ttl > 0 and forward_message.max_recursive_contact > 0:
        contacts = await database.list_contacts()
        logger.info(f"[FORWARD_TASK] Found {len(contacts)} total contacts")
        
        # Filter out sender node
        eligible_contacts = [
            c for c in contacts 
            if c.identifier != message.current_node_identifier
        ]
        
        if not eligible_contacts:
            logger.warning(f"[FORWARD_TASK] No eligible contacts for forwarding")
            return
        total_contacts = len(eligible_contacts)
        # Random node selection for privacy and efficiency
        # Select 30%-100% of contacts, max 10 nodes
        min_contacts = max(1, int(total_contacts * 0.3))
        max_contacts = int(total_contacts * 0.7)
        num_contacts = random.randint(min_contacts, max_contacts)
        
        selected_contacts = random.sample(eligible_contacts, num_contacts)
        
        logger.info(f"[FORWARD_TASK] Randomly selected {num_contacts}/{len(eligible_contacts)} contacts for forwarding")
        if default_logger:
            default_logger.log("RANDOM_SELECT", 
                             group="Routing", 
                             selected=num_contacts,
                             total=len(eligible_contacts))

        # Use auto-proxy client - will detect I2P destinations and route through proxy
        async with create_http_client() as client:
            for contact in selected_contacts:
                logger.info(f"[FORWARD_TASK] Attempting to forward to {contact.name or contact.identifier} at {contact.addr}")
                try:
                    resp = await client.post(
                        contact.addr + "/send",
                        json=forward_message.model_dump(),
                        timeout=5.0
                    )
                    resp.raise_for_status()
                    logger.info(f"[FORWARD_TASK] Successfully forwarded to {contact.addr}")
                    
                    if default_logger:
                        default_logger.log("FORWARD_SUCCESS", 
                                         group="Routing", 
                                         target=contact.identifier[:8],
                                         addr=contact.addr)
                except httpx.HTTPError as e:
                    logger.warning(f"[FORWARD_TASK] Failed to forward to {contact.addr}: {e}")
                    
                    if default_logger:
                        default_logger.log("FORWARD_FAILED", 
                                         group="Routing", 
                                         target=contact.identifier[:8],
                                         error=str(e)[:50])
                else:
                    if contact.identifier == message.recipient_identifier:
                        logger.info(f"[FORWARD_TASK] Message delivered to final recipient: {contact.identifier}")
                        await database.delete_forward_message(message.recipient_identifier)
                        return
    else:
        logger.warning(f"[FORWARD_TASK] Message dropped - TTL={forward_message.ttl}, Max recursive={forward_message.max_recursive_contact}")
def add_routers(app: FastAPI, messanger: SecureMessenger, database: Database) -> FastAPI:
    logger.info(f"[INIT] Adding routers for messenger with ID: {messanger.identifier}")
    
    @app.post("/send")
    async def send_message(message: MessageModel):
        logger.info(f"[RECEIVE] Incoming message - Signature: {message.signature[:16]}...")
        logger.info(f"[RECEIVE] Recipient: {message.recipient_identifier[:16]}..., Current node: {message.current_node_identifier[:16]}..., TTL: {message.ttl}")
        
        if default_logger:
            default_logger.log("MSG_RECEIVED", 
                             group="Messaging", 
                             signature=message.signature[:8],
                             ttl=message.ttl)
        
        # Check if we've seen this message before (prevent loops)
        if await database.get_entry(message.signature):
            logger.info(f"[RECEIVE] Message already seen (signature: {message.signature[:16]}...), ignoring")
            
            if default_logger:
                default_logger.log("MSG_DUPLICATE", 
                                 group="Messaging", 
                                 signature=message.signature[:8])
            return {"status": "OK"}
        
        # Mark message as seen
        await database.add_entry(message.signature)
        logger.info(f"[RECEIVE] Marked message as seen")
        
        # Check if message is for this node
        if message.recipient_identifier == messanger.identifier:
            logger.info(f"[RECEIVE] Message is for this node, decrypting...")
            
            if default_logger:
                default_logger.log("MSG_FOR_ME", 
                                 group="Messaging", 
                                 signature=message.signature[:8])
            
            try:
                msg = messanger.decrypt_message(message.model_dump())
                logger.info(f"[DECRYPT] Successfully decrypted message from {msg['sender_id'][:16]}...")
                
                if default_logger:
                    default_logger.log("DECRYPT_SUCCESS", 
                                     group="Messaging", 
                                     sender=msg['sender_id'][:8])
                
                # Add sender as contact if not exists
                if await database.get_contact(msg["sender_id"]) is None:
                    logger.info(f"[CONTACT] Adding new contact: {msg['sender_id'][:16]}...")
                    await database.add_contact(
                        identifier=msg["sender_id"], 
                        kem_public_key=msg["kem_public_key"], 
                        sign_public_key=msg["signature_public_key"], 
                        addr=msg["sender_dest"]
                    )
                    
                    if default_logger:
                        default_logger.log("CONTACT_ADDED", 
                                         group="Contacts", 
                                         contact_id=msg["sender_id"][:8])
                else:
                    logger.info(f"[CONTACT] Sender already in contacts")
                
                # Save message with sender_id and recipient_id
                await database.add_message(
                    content=msg["message"],
                    timestamp=msg["timestamp"],
                    sender_id=msg["sender_id"],
                    recipient_id=messanger.identifier  # Save recipient ID for self-messages
                )
                logger.info(f"[STORAGE] Message saved to database")
                
                if default_logger:
                    default_logger.log("MSG_STORED", 
                                     group="Storage", 
                                     sender=msg["sender_id"][:8],
                                     recipient=messanger.identifier[:8])
                
                return {"status": "OK"}
            except Exception as e:
                logger.error(f"[DECRYPT] Failed to decrypt message: {e}")
                
                if default_logger:
                    default_logger.log("DECRYPT_FAILED", 
                                     group="Messaging", 
                                     error=str(e)[:50])
                return {"status": "ERROR", "message": "Decryption failed"}
        
        # Message is not for this node, prepare to forward
        logger.info(f"[FORWARD] Message not for this node, preparing to forward with random node selection")
        
        if default_logger:
            default_logger.log("MSG_FORWARD", 
                             group="Routing", 
                             recipient=message.recipient_identifier[:8],
                             ttl=message.ttl)
        
        forward_message = message.model_copy()
        
        # Check if we know the recipient
        if await database.get_contact(message.recipient_identifier):
            logger.info(f"[FORWARD] Recipient in contacts, saving forward message")
            await database.add_forward_message(
                recipient_identifier=message.recipient_identifier, 
                shared_secret_ciphertext=message.shared_secret_ciphertext, 
                message_ciphertext=message.message_ciphertext, 
                nonce=message.nonce, 
                signature=message.signature
            )
            # Random decrement for max_recursive_contact (0-2) for traffic analysis protection
            random_decrement_recursive = random.randint(0, 2)
            forward_message.max_recursive_contact -= random_decrement_recursive
            logger.info(f"[FORWARD] Max recursive contacts decremented by {random_decrement_recursive} to {forward_message.max_recursive_contact}")
        else:
            logger.info(f"[FORWARD] Recipient not in contacts, flooding mode")
        
        # Update current node identifier
        forward_message.current_node_identifier = messanger.identifier
        
        # Random decrement for TTL (0-2) for traffic analysis protection
        # This prevents observers from calculating exact distance to origin
        random_decrement_ttl = random.randint(0, 2)
        forward_message.ttl -= random_decrement_ttl
        logger.info(f"[FORWARD] TTL decremented by {random_decrement_ttl} to {forward_message.ttl}")
        
        # Launch forwarding task in background
        asyncio.create_task(forward_message_task(forward_message, message, database))
        logger.info(f"[FORWARD] Background forwarding task started")
        
        return {"status": "OK"}
    
    @app.post("/get_messages/{identifier}")
    async def get_messages(identifier: str):
        logger.info(f"[API] Getting forwarded messages for identifier: {identifier[:16]}...")
        
        if default_logger:
            default_logger.log("GET_MESSAGES", 
                             group="API", 
                             identifier=identifier[:8])
        
        messages = await database.get_for_contact(identifier)
        logger.info(f"[API] Found {len(messages)} forwarded messages")
        
        return {"messages": messages}
    
    return app