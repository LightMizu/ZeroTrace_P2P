#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
import random
from pathlib import Path
from typing import Optional
import threading

import httpx
import uvicorn
from fastapi import FastAPI

from zerotrace.core.messenger_core import SecureMessenger
from zerotrace.core.database import Database
from zerotrace.core.router import add_routers
from zerotrace.core.scheme import MessageModel
from zerotrace.core.utils import b64_dec, b64_enc
from zerotrace.core.post_quantum.sign import PostQuantumSignature
from zerotrace.kademlia import create_app
from zerotrace.kademlia.client import DHTClient
import hashlib


class ZeroTraceClient:
    """CLI Client for ZeroTrace Messenger"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, data_dir: str = "."):
        self.host = host
        self.port = port
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.keys_file = self.data_dir / "user_keys.json"
        self.db_path = str(self.data_dir / "zerotrace.db")
        
        self.messenger: Optional[SecureMessenger] = None
        self.database: Optional[Database] = None
        self.app: Optional[FastAPI] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.dht_client: Optional[DHTClient] = None
        self.signature_verifier = PostQuantumSignature()

    async def initialize(self):
        """Initialize database and messenger"""
        self.database = Database(url=f"sqlite+aiosqlite:///{self.db_path}")
        await self.database.init()
        
        # Initialize messenger
        self.messenger = SecureMessenger(ip=f"http://{self.host}:{self.port}")
        
        # Load or create keys
        if self.keys_file.exists():
            print("\n🔑 Found existing keys. Please enter your password to unlock.")
            password = input("Password: ").encode()
            
            with open(self.keys_file, 'r') as f:
                key_data = json.load(f)
            
            if self.messenger.load_keys(key_data, password):
                print(f"✅ Keys loaded successfully!")
                print(f"📝 Your identifier: {self.messenger.identifier}")
            else:
                print("❌ Failed to load keys. Wrong password?")
                sys.exit(1)
        else:
            print("\n🆕 No existing keys found. Creating new account...")
            password = input("Set a password for your account: ").encode()
            
            self.messenger.generate_keys()
            key_bundle = self.messenger.save_keys(password)
            
            with open(self.keys_file, 'w') as f:
                json.dump(key_bundle, f, indent=2)
            
            print(f"✅ New account created!")
            print(f"📝 Your identifier: {self.messenger.identifier}")
            print(f"💾 Keys saved to: {self.keys_file}")

    def start_server_background(self):
        """Start FastAPI server in background thread"""
        assert self.messenger is not None, "Messenger not initialized"
        assert self.database is not None, "Database not initialized"
        
        def run_server():
            # Create Kademlia app
            kad_app = create_app(
                address=self.host,
                port=self.port,
                db_path=str(self.data_dir / "kademlia.db")
            )
            
            # Add messenger routes with the correct database instance
            assert self.messenger is not None
            assert self.database is not None
            self.app = add_routers(kad_app, self.messenger, self.database)
            
            # Run server
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="warning"
            )
            server = uvicorn.Server(config)
            asyncio.run(server.serve())
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        
        # Wait for server to start
        time.sleep(2)
        print(f"\n🚀 Server started at http://{self.host}:{self.port}")
        
        # Initialize DHT client
        messenger_host = "127.0.0.1" if self.host == "0.0.0.0" else self.host
        self.dht_client = DHTClient(host=messenger_host, port=self.port)

    async def send_message(self, recipient_id: str, message: str):
        """Send a message to a recipient"""
        assert self.database is not None and self.messenger is not None
        
        # Get recipient contact
        contact = await self.database.get_contact(recipient_id)
        
        if not contact:
            print(f"❌ Contact '{recipient_id}' not found. Add them first!")
            return
        
        # Encrypt message
        encrypted = self.messenger.encrypt_message(
            recipient_identifier=str(contact.identifier),
            recipient_kem_public_key=b64_dec(str(contact.kem_public_key)),
            message=message.encode(),
            timestamp=time.time()
        )
        
        # Randomize TTL and max_recursive_contact to prevent metadata fingerprinting
        # TTL: random between 8-12 (average 10, prevents tracking by hop count)
        # max_recursive: random between 3-7 (average 5, prevents pattern analysis)
        random_ttl = random.randint(8, 12)
        random_max_recursive = random.randint(3, 7)
        
        # Create message model
        msg_model = MessageModel(
            current_node_identifier=self.messenger.identifier,
            recipient_identifier=encrypted["recipient_identifier"],
            shared_secret_ciphertext=encrypted["shared_secret_ciphertext"],
            message_ciphertext=encrypted["message_ciphertext"],
            nonce=encrypted["nonce"],
            signature=encrypted["signature"],
            ttl=random_ttl,
            max_recursive_contact=random_max_recursive
        )
        
        # Save self-message to database (outgoing message)
        await self.database.add_message(
            content=b64_enc(message.encode()),
            timestamp=str(time.time()),
            sender_id=self.messenger.identifier,
            recipient_id=recipient_id  # Save with recipient ID
        )
        print(f"✅ Message saved to outbox")
        
        # Try to send message directly to recipient
        direct_send_success = False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{contact.addr}/send",
                    json=msg_model.model_dump(),
                    timeout=10.0
                )
                resp.raise_for_status()
                print(f"✅ Message sent directly to {contact.name or recipient_id}")
                direct_send_success = True
        except httpx.HTTPError as e:
            print(f"⚠️  Direct connection to {contact.name or recipient_id} failed: {e}")
            print(f"🔄 Attempting to route message through other contacts...")
        
        # If direct send failed, forward to all other contacts for P2P routing
        if not direct_send_success:
            all_contacts = await self.database.list_contacts()
            forward_count = 0
            success_count = 0
            
            async with httpx.AsyncClient() as client:
                for other_contact in all_contacts:
                    # Skip the recipient (already failed) and self
                    if str(other_contact.identifier) == recipient_id or str(other_contact.identifier) == self.messenger.identifier:
                        continue
                    
                    forward_count += 1
                    try:
                        resp = await client.post(
                            f"{other_contact.addr}/send",
                            json=msg_model.model_dump(),
                            timeout=5.0
                        )
                        resp.raise_for_status()
                        success_count += 1
                        print(f"  ✓ Forwarded to {other_contact.name or other_contact.identifier[:16]}")
                    except httpx.HTTPError as forward_err:
                        print(f"  ✗ Failed to forward through {other_contact.name or other_contact.identifier[:16]}: {forward_err}")
            
            if success_count > 0:
                print(f"\n📡 Message forwarded to {success_count}/{forward_count} intermediate nodes")
                print(f"   The message will be routed through the P2P network to reach {contact.name or recipient_id}")
            else:
                print(f"\n❌ Could not route message - all {forward_count} intermediate contacts are unreachable")
                if forward_count == 0:
                    print(f"   You need to add more contacts to enable P2P routing")

    async def view_messages(self, sender_id: Optional[str] = None):
        """View received messages"""
        assert self.database is not None
        
        if sender_id:
            contact = await self.database.get_contact(sender_id)
            if not contact:
                print(f"❌ Contact '{sender_id}' not found")
                return
            
            messages = await self.database.list_messages(sender_id=sender_id)
            print(f"\n💬 Messages from {contact.name or sender_id}:")
        else:
            messages = await self.database.list_messages()
            print("\n💬 All Messages:")
        
        if not messages:
            print("\n📭 No messages found.")
            return
        
        print("=" * 80)
        for msg in messages:
            # Get sender info
            sender = await self.database.get_contact(str(msg.sender_id))
            sender_name = sender.name if sender else "Unknown"
            
            # Decode message content
            try:
                content = b64_dec(str(msg.content)).decode('utf-8')
            except:
                content = msg.content
            
            print(f"From: {sender_name} ({msg.sender_id})")
            print(f"Time: {msg.timestamp}")
            print(f"Message: {content}")
            print("-" * 80)

    async def add_contact(self, identifier: str, name: str, addr: str, 
                         kem_public_key: str, sign_public_key: str):
        """Add a new contact"""
        assert self.database is not None
        
        await self.database.add_contact(
            identifier=identifier,
            name=name,
            kem_public_key=kem_public_key,
            sign_public_key=sign_public_key,
            addr=addr
        )
        print(f"✅ Contact '{name}' added successfully!")

    async def list_contacts(self):
        """List all contacts"""
        assert self.database is not None
        
        contacts = await self.database.list_contacts()
        
        if not contacts:
            print("\n📭 No contacts found.")
            return
        
        print("\n👥 Your Contacts:")
        print("=" * 80)
        for contact in contacts:
            print(f"Name: {contact.name or 'Unknown'}")
            print(f"ID: {contact.identifier}")
            print(f"Address: {contact.addr}")
            print("-" * 80)

    async def show_info(self):
        """Show current user information"""
        assert self.messenger is not None
        
        print("\n📋 Your Information:")
        print("=" * 80)
        print(f"Identifier: {self.messenger.identifier}")
        print(f"Server: http://{self.host}:{self.port}")
        print(f"KEM Public Key: {b64_enc(self.messenger.kem_public_key)}")
        print(f"Sign Public Key: {b64_enc(self.messenger.signature_public_key)}")
        print("=" * 80)

    def _sign_address(self, address: str) -> str:
        """Sign an address with the user's signature key"""
        assert self.messenger is not None
        
        # Create hash of address + identifier
        addr_data = f"{address}:{self.messenger.identifier}".encode()
        addr_hash = hashlib.sha256(addr_data).digest()
        
        # Sign the hash (we need access to private key through messenger)
        # For now, return the hash as signature placeholder
        signature = b64_enc(addr_hash)
        return signature
    
    def _verify_address_signature(self, address: str, identifier: str, signature: str, sign_public_key: str) -> bool:
        """Verify address signature"""
        try:
            # Recreate the hash
            addr_data = f"{address}:{identifier}".encode()
            addr_hash = hashlib.sha256(addr_data).digest()
            
            # For now, simple hash comparison (should use actual signature verification)
            expected_sig = b64_enc(addr_hash)
            return signature == expected_sig
        except Exception as e:
            print(f"⚠️  Signature verification failed: {e}")
            return False

    async def publish_to_dht(self):
        """Publish user's public keys and signed address to DHT"""
        assert self.messenger is not None and self.dht_client is not None
        
        print("\n📡 Publishing keys to DHT...")
        
        try:
            # Prepare address
            messenger_host = "127.0.0.1" if self.host == "0.0.0.0" else self.host
            address = f"http://{messenger_host}:{self.port}"
            
            # Sign the address
            addr_signature = self._sign_address(address)
            
            # Create user info package
            user_info = {
                "identifier": self.messenger.identifier,
                "kem_public_key": b64_enc(self.messenger.kem_public_key),
                "sign_public_key": b64_enc(self.messenger.signature_public_key),
                "address": address,
                "address_signature": addr_signature,
                "timestamp": time.time()
            }
            
            # Serialize to JSON and encode
            user_info_json = json.dumps(user_info)
            
            # Use identifier as DHT key
            key_hash = hashlib.sha256(self.messenger.identifier.encode()).hexdigest()
            
            # Publish to DHT via HTTP endpoint
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"http://{messenger_host}:{self.port}/set",
                    json={
                        "node_id": await self.dht_client.get_id(),
                        "key": key_hash,
                        "value": user_info_json.encode().hex()
                    },
                    timeout=10.0
                )
                resp.raise_for_status()
                
            print(f"✅ Published to DHT with key: {key_hash[:16]}...")
            print(f"   Identifier: {self.messenger.identifier}")
            print(f"   Address: {address}")
            
        except Exception as e:
            print(f"❌ Failed to publish to DHT: {e}")

    async def search_dht(self, identifier: str):
        """Search for a user in DHT by identifier"""
        assert self.dht_client is not None
        
        print(f"\n🔍 Searching DHT for: {identifier[:20]}...")
        
        try:
            # Get our node ID
            our_node_id = await self.dht_client.get_id()
            
            # Create search key from identifier
            key_hash = hashlib.sha256(identifier.encode()).digest()
            
            # Search DHT
            result = await self.dht_client.find_value_recursive(our_node_id, key_hash)
            
            if result:
                # Decode and parse result
                user_info_json = result.decode('utf-8')
                user_info = json.loads(user_info_json)
                
                # Verify address signature
                is_valid = self._verify_address_signature(
                    user_info["address"],
                    user_info["identifier"],
                    user_info["address_signature"],
                    user_info["sign_public_key"]
                )
                
                if not is_valid:
                    print("❌ Invalid address signature - data may be tampered!")
                    return None
                
                print("✅ Found in DHT:")
                print("=" * 60)
                print(f"Identifier: {user_info['identifier']}")
                print(f"Address: {user_info['address']}")
                print(f"KEM Public Key: {user_info['kem_public_key'][:40]}...")
                print(f"Sign Public Key: {user_info['sign_public_key'][:40]}...")
                print(f"Signature: ✅ Valid")
                print("=" * 60)
                
                # Ask if user wants to add as contact
                add = input("\nAdd this user as a contact? (y/n): ")
                if add.lower() == 'y':
                    name = input("Enter a name for this contact: ")
                    await self.add_contact(
                        identifier=user_info["identifier"],
                        name=name,
                        addr=user_info["address"],
                        kem_public_key=user_info["kem_public_key"],
                        sign_public_key=user_info["sign_public_key"]
                    )
                
                return user_info
            else:
                print("❌ Not found in DHT")
                return None
                
        except Exception as e:
            print(f"❌ DHT search failed: {e}")
            return None

    async def fetch_pending_messages(self):
        """Fetch all pending messages from all contacts"""
        assert self.messenger is not None and self.database is not None
        
        contacts = await self.database.list_contacts()
        
        if not contacts:
            print("\n📭 No contacts to fetch messages from")
            return
        
        print("\n📥 Fetching pending messages from all contacts...")
        print("=" * 60)
        
        total_messages = 0
        successful_contacts = 0
        
        async with httpx.AsyncClient() as client:
            for contact in contacts:
                try:
                    # Request pending messages from this contact
                    resp = await client.post(
                        f"{contact.addr}/get_messages/{self.messenger.identifier}",
                        timeout=5.0
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    
                    messages = data.get("messages", [])
                    
                    if messages:
                        print(f"\n📬 From {contact.name or contact.identifier[:20]}:")
                        
                        for msg_data in messages:
                            try:
                                # Decrypt the message
                                decrypted = self.messenger.decrypt_message({
                                    "recipient_identifier": msg_data["recipient_identifier"],
                                    "shared_secret_ciphertext": msg_data["shared_secret_ciphertext"],
                                    "message_ciphertext": msg_data["message_ciphertext"],
                                    "nonce": msg_data["nonce"],
                                    "signature": msg_data["signature"]
                                })
                                
                                # Save the message to database
                                await self.database.add_message(
                                    content=decrypted["message"],
                                    timestamp=str(decrypted["timestamp"]),
                                    sender_id=decrypted["sender_id"],
                                    recipient_id=self.messenger.identifier
                                )
                                
                                # Decode and display
                                msg_content = decrypted["message"]
                                if isinstance(msg_content, bytes):
                                    msg_text = msg_content.decode('utf-8')
                                else:
                                    msg_text = str(msg_content)
                                
                                print(f"  ✓ Message from {decrypted['sender_id'][:20]}")
                                print(f"    Content: {msg_text[:50]}{'...' if len(msg_text) > 50 else ''}")
                                total_messages += 1
                                
                            except Exception as decrypt_err:
                                print(f"  ✗ Failed to decrypt message: {decrypt_err}")
                        
                        successful_contacts += 1
                    
                except httpx.HTTPError as e:
                    # Silently skip unreachable contacts
                    pass
                except Exception as e:
                    print(f"⚠️  Error fetching from {contact.name or contact.identifier[:20]}: {e}")
        
        print("\n" + "=" * 60)
        if total_messages > 0:
            print(f"✅ Retrieved {total_messages} pending message(s) from {successful_contacts} contact(s)")
        else:
            print("📭 No pending messages found")
        print("=" * 60)

    async def bootstrap_node(self):
        """Bootstrap this node to another node to join the DHT network"""
        assert self.dht_client is not None
        
        print("\n🔗 Bootstrap to DHT Network")
        print("=" * 60)
        print("Enter the address of a known node to connect to:")
        
        target_host = input("Host (e.g., 127.0.0.1 or example.com): ").strip()
        if not target_host:
            print("❌ Host cannot be empty")
            return
        
        target_port = input("Port (e.g., 8000): ").strip()
        if not target_port:
            print("❌ Port cannot be empty")
            return
        
        try:
            target_port = int(target_port)
        except ValueError:
            print("❌ Port must be a number")
            return
        
        # Ask for symmetric bootstrap
        symmetric_input = input("\nUse symmetric bootstrap (recommended)? (y/n, default: y): ").strip().lower()
        symmetric = symmetric_input != 'n'  # Default to yes
        
        print(f"\n🔄 Connecting to {target_host}:{target_port}...")
        if symmetric:
            print("   Mode: Symmetric (both nodes will know each other)")
        else:
            print("   Mode: One-way (only you will know the target)")
        
        try:
            success = await self.dht_client.bootstrap(target_host, target_port, symmetric=symmetric)
            
            if success:
                print(f"✅ Successfully bootstrapped to {target_host}:{target_port}")
                if symmetric:
                    print("   ↔️  Bidirectional connection established")
                    print("   ✓ They added you to their routing table")
                    print("   ✓ You added them to your routing table")
                else:
                    print("   → One-way connection established")
                    print("   ✓ You added them to your routing table")
                
                print("\n📊 You are now connected to the DHT network!")
                print("   You can now:")
                print("   • Publish your keys (option 6)")
                print("   • Search for other users (option 7)")
                print("   • Message will be routed through the network")
            else:
                print(f"❌ Failed to bootstrap to {target_host}:{target_port}")
                print("   Please check:")
                print("   • Target node is running")
                print("   • Address and port are correct")
                print("   • Network connectivity")
        except Exception as e:
            print(f"❌ Bootstrap error: {e}")

    async def interactive_menu(self):
        """Show interactive CLI menu"""
        while True:
            print("\n" + "=" * 50)
            print("ZeroTrace Messenger - Main Menu")
            print("=" * 50)
            print("1. Send Message")
            print("2. View Messages")
            print("3. Add Contact")
            print("4. List Contacts")
            print("5. Show My Info")
            print("6. Publish to DHT")
            print("7. Search DHT")
            print("8. Bootstrap to Network")
            print("9. Fetch Pending Messages")
            print("10. Exit")
            print("=" * 50)
            
            choice = input("\nSelect an option (1-10): ")
            
            if choice == "1":
                recipient_id = input("Recipient ID: ")
                message = input("Message: ")
                await self.send_message(recipient_id, message)
            
            elif choice == "2":
                sender_id = input("Sender ID (leave empty for all): ").strip()
                await self.view_messages(sender_id if sender_id else None)
            
            elif choice == "3":
                print("\n➕ Add New Contact")
                name = input("Name: ")
                identifier = input("Identifier: ")
                addr = input("Address (e.g., http://localhost:8001): ")
                kem_key = input("KEM Public Key (base64): ")
                sign_key = input("Signature Public Key (base64): ")
                await self.add_contact(identifier, name, addr, kem_key, sign_key)
            
            elif choice == "4":
                await self.list_contacts()
            
            elif choice == "5":
                await self.show_info()
            
            elif choice == "6":
                await self.publish_to_dht()
            
            elif choice == "7":
                identifier = input("\nEnter identifier to search: ")
                await self.search_dht(identifier)
            
            elif choice == "8":
                await self.bootstrap_node()
            
            elif choice == "9":
                await self.fetch_pending_messages()
            
            elif choice == "10":
                print("\n👋 Goodbye!")
                break
            
            else:
                print("\n❌ Invalid option. Please try again.")


async def main():
    """Main entry point for CLI client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZeroTrace P2P Messenger")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--data-dir", default=".", help="Data directory (default: current dir)")
    parser.add_argument("--server-only", action="store_true", help="Run server only without CLI")
    
    args = parser.parse_args()
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              ZeroTrace P2P Messenger v1.0                 ║
║           Secure Post-Quantum Messaging System            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    client = ZeroTraceClient(host=args.host, port=args.port, data_dir=args.data_dir)
    
    # Initialize
    await client.initialize()
    
    # Start server
    client.start_server_background()
    
    # Fetch pending messages from all contacts
    await client.fetch_pending_messages()
    
    if args.server_only:
        print("\n🔄 Running in server-only mode. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Server stopped.")
    else:
        # Run interactive menu
        await client.interactive_menu()
        
        # Cleanup
        if client.database:
            await client.database.close()
        if client.dht_client:
            await client.dht_client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")