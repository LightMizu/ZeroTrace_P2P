#!/usr/bin/env python3
"""
Example script demonstrating programmatic usage of ZeroTrace messenger.
This can be used as a reference for automation or integration.
"""

import asyncio
import json
from pathlib import Path
from zerotrace.core.messenger_core import SecureMessenger
from zerotrace.core.database import Database
from zerotrace.core.utils import b64_enc, b64_dec


async def create_user(name: str, port: int):
    """Create a new user with keys and database"""
    print(f"\n🔧 Creating user: {name}")
    
    # Setup
    data_dir = Path(f"./{name}_data")
    data_dir.mkdir(exist_ok=True)
    
    # Initialize messenger
    messenger = SecureMessenger(ip=f"http://localhost:{port}")
    messenger.generate_keys()
    
    # Save keys
    password = f"{name}_password".encode()
    key_bundle = messenger.save_keys(password)
    
    keys_file = data_dir / "keys.json"
    with open(keys_file, 'w') as f:
        json.dump(key_bundle, f, indent=2)
    
    # Initialize database
    db = Database(url=f"sqlite+aiosqlite:///{data_dir}/messages.db")
    await db.init()
    
    print(f"✅ User created: {name}")
    print(f"   Identifier: {messenger.identifier}")
    print(f"   Port: {port}")
    print(f"   Data dir: {data_dir}")
    
    return {
        "name": name,
        "messenger": messenger,
        "database": db,
        "identifier": messenger.identifier,
        "kem_public_key": b64_enc(messenger.kem_public_key),
        "sign_public_key": b64_enc(messenger.signature_public_key),
        "port": port,
        "addr": f"http://localhost:{port}"
    }


async def send_message(sender, recipient, message_text: str):
    """Send a message from sender to recipient"""
    print(f"\n📤 {sender['name']} sending message to {recipient['name']}")
    
    # Add recipient as contact if not exists
    contact = await sender['database'].get_contact(recipient['identifier'])
    if not contact:
        await sender['database'].add_contact(
            identifier=recipient['identifier'],
            name=recipient['name'],
            kem_public_key=recipient['kem_public_key'],
            sign_public_key=recipient['sign_public_key'],
            addr=recipient['addr']
        )
        print(f"   ➕ Added {recipient['name']} as contact")
    
    # Encrypt message
    import time
    encrypted = sender['messenger'].encrypt_message(
        recipient_kem_public_key=b64_dec(recipient['kem_public_key']),
        message=message_text.encode(),
        timestamp=time.time()
    )
    
    print(f"   🔐 Message encrypted")
    print(f"   📝 Message: {message_text}")
    
    # In a real scenario, this would be sent via HTTP
    # For this example, we'll simulate by directly decrypting
    return encrypted


async def receive_message(recipient, encrypted_msg):
    """Receive and decrypt a message"""
    print(f"\n📥 {recipient['name']} receiving message")
    
    # Decrypt
    decrypted = recipient['messenger'].decrypt_message(encrypted_msg)
    
    if "result" in decrypted:
        print(f"   ❌ Failed: {decrypted['result']}")
        return None
    
    message_text = decrypted['message'].decode('utf-8')
    sender_id = decrypted['sender_id']
    
    print(f"   🔓 Message decrypted")
    print(f"   From: {sender_id}")
    print(f"   Message: {message_text}")
    
    # Store in database
    await recipient['database'].add_message(
        content=b64_enc(decrypted['message']),
        timestamp=str(decrypted['timestamp']),
        sender_id=sender_id
    )
    
    # Add sender as contact if not exists
    contact = await recipient['database'].get_contact(sender_id)
    if not contact:
        await recipient['database'].add_contact(
            identifier=sender_id,
            name="Unknown",
            kem_public_key=decrypted['kem_public_key'],
            sign_public_key=decrypted['signature_public_key'],
            addr=decrypted['sender_dest']
        )
    
    return decrypted


async def main():
    """Demo: Create two users and exchange messages"""
    
    print("=" * 60)
    print("ZeroTrace Messenger - Example Usage")
    print("=" * 60)
    
    # Create two users
    alice = await create_user("Alice", 8000)
    bob = await create_user("Bob", 8001)
    
    print("\n" + "=" * 60)
    print("User Information")
    print("=" * 60)
    
    print(f"\n👤 Alice")
    print(f"   ID: {alice['identifier']}")
    print(f"   KEM Key: {alice['kem_public_key'][:40]}...")
    print(f"   Sign Key: {alice['sign_public_key'][:40]}...")
    
    print(f"\n👤 Bob")
    print(f"   ID: {bob['identifier']}")
    print(f"   KEM Key: {bob['kem_public_key'][:40]}...")
    print(f"   Sign Key: {bob['sign_public_key'][:40]}...")
    
    # Exchange messages
    print("\n" + "=" * 60)
    print("Message Exchange")
    print("=" * 60)
    
    # Alice sends to Bob
    msg1 = await send_message(alice, bob, "Hello Bob! How are you?")
    await receive_message(bob, msg1)
    
    # Bob replies to Alice
    msg2 = await send_message(bob, alice, "Hi Alice! I'm doing great, thanks!")
    await receive_message(alice, msg2)
    
    # Alice sends another message
    msg3 = await send_message(alice, bob, "Great to hear! Let's meet tomorrow.")
    await receive_message(bob, msg3)
    
    # List Bob's messages
    print("\n" + "=" * 60)
    print("Bob's Inbox")
    print("=" * 60)
    
    messages = await bob['database'].list_messages()
    for i, msg in enumerate(messages, 1):
        content = b64_dec(msg.content).decode('utf-8')
        print(f"\n{i}. From: {msg.sender_id[:20]}...")
        print(f"   Time: {msg.timestamp}")
        print(f"   Message: {content}")
    
    # List contacts
    print("\n" + "=" * 60)
    print("Bob's Contacts")
    print("=" * 60)
    
    contacts = await bob['database'].list_contacts()
    for contact in contacts:
        print(f"\n👤 {contact.name}")
        print(f"   ID: {contact.identifier[:40]}...")
        print(f"   Address: {contact.addr}")
    
    # Cleanup
    await alice['database'].close()
    await bob['database'].close()
    
    print("\n" + "=" * 60)
    print("✅ Example completed successfully!")
    print("=" * 60)
    
    print("\n💡 To run the actual CLI:")
    print("   python -m zerotrace.main")
    print("\n💡 To run server only:")
    print("   python -m zerotrace.main --server-only --port 8000")


if __name__ == "__main__":
    asyncio.run(main())
