#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
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
from zerotrace.kademlia import create_app


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
        
        def run_server():
            # Create Kademlia app
            kad_app = create_app(
                address=self.host,
                port=self.port,
                db_path=str(self.data_dir / "kademlia.db")
            )
            
            # Add messenger routes
            assert self.messenger is not None
            self.app = add_routers(kad_app, self.messenger)
            
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
            recipient_kem_public_key=b64_dec(contact.kem_public_key),
            message=message.encode(),
            timestamp=time.time()
        )
        
        # Create message model
        msg_model = MessageModel(
            current_node_identifier=self.messenger.identifier,
            recipient_identifier=encrypted["recipient_identifier"],
            shared_secret_ciphertext=encrypted["shared_secret_ciphertext"],
            message_ciphertext=encrypted["message_ciphertext"],
            nonce=encrypted["nonce"],
            signature=encrypted["signature"],
            ttl=10,
            max_recursive_contact=5
        )
        
        # Send message
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{contact.addr}/send",
                    json=msg_model.model_dump(),
                    timeout=10.0
                )
                resp.raise_for_status()
                print(f"✅ Message sent to {contact.name or recipient_id}")
        except httpx.HTTPError as e:
            print(f"❌ Failed to send message: {e}")

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
            sender = await self.database.get_contact(msg.sender_id)
            sender_name = sender.name if sender else "Unknown"
            
            # Decode message content
            try:
                content = b64_dec(msg.content).decode('utf-8')
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
            print("6. Exit")
            print("=" * 50)
            
            choice = input("\nSelect an option (1-6): ")
            
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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")