# ZeroTrace CLI Messenger - Usage Guide

## Overview

ZeroTrace is a secure P2P messaging system with post-quantum cryptography. The CLI client provides an interactive interface for secure messaging.

## Features

- 🔐 Post-quantum cryptographic key generation
- 💬 Secure end-to-end encrypted messaging
- 👥 Contact management
- 🌐 P2P network with Kademlia DHT
- 🔄 Message forwarding and routing
- 💾 Local database storage

## Installation

Make sure you have all dependencies installed:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Start the CLI Client

```bash
python -m zerotrace.main
```

Or with custom options:

```bash
python -m zerotrace.main --host 0.0.0.0 --port 8000 --data-dir ./data
```

### 2. First Time Setup

On first run, you'll be prompted to create a new account:

```
🆕 No existing keys found. Creating new account...
Set a password for your account: ********
```

Your cryptographic keys will be generated and encrypted with your password. You'll see:

```
✅ New account created!
📝 Your identifier: [your-unique-id]
💾 Keys saved to: user_keys.json
```

### 3. Subsequent Runs

On subsequent runs, you'll need to unlock your account:

```
🔑 Found existing keys. Please enter your password to unlock.
Password: ********
✅ Keys loaded successfully!
📝 Your identifier: [your-unique-id]
```

## CLI Commands

### Main Menu Options

```
==================================================
ZeroTrace Messenger - Main Menu
==================================================
1. Send Message
2. View Messages
3. Add Contact
4. List Contacts
5. Show My Info
6. Exit
==================================================
```

### 1. Send Message

Send an encrypted message to a contact:

1. Select option `1`
2. Enter the recipient's identifier
3. Type your message
4. Message will be encrypted and sent through the P2P network

Example:
```
Select an option (1-6): 1
Recipient ID: alice-identifier-here
Message: Hello Alice!
✅ Message sent to Alice
```

### 2. View Messages

View received messages:

1. Select option `2`
2. Enter sender ID (or leave empty to see all messages)
3. View message list with sender info, timestamps, and content

Example:
```
Select an option (1-6): 2
Sender ID (leave empty for all): 

📬 All Messages:
================================================================================
From: Alice (alice-identifier)
Time: 2025-10-20 12:30:45
Message: Hello Bob!
--------------------------------------------------------------------------------
```

### 3. Add Contact

Add a new contact to your address book:

1. Select option `3`
2. Enter contact details:
   - Name (friendly name)
   - Identifier (their unique ID)
   - Address (their server URL, e.g., http://localhost:8001)
   - KEM Public Key (base64 encoded)
   - Signature Public Key (base64 encoded)

Example:
```
Select an option (1-6): 3

➕ Add New Contact
Name: Alice
Identifier: alice-identifier
Address (e.g., http://localhost:8001): http://192.168.1.100:8001
KEM Public Key (base64): [paste-kem-key]
Signature Public Key (base64): [paste-sign-key]
✅ Contact 'Alice' added successfully!
```

### 4. List Contacts

View all your contacts:

```
Select an option (1-6): 4

👥 Your Contacts:
================================================================================
Name: Alice
ID: alice-identifier
Address: http://192.168.1.100:8001
--------------------------------------------------------------------------------
Name: Bob
ID: bob-identifier
Address: http://192.168.1.200:8002
--------------------------------------------------------------------------------
```

### 5. Show My Info

Display your account information (share this with others so they can add you):

```
Select an option (1-6): 5

📋 Your Information:
================================================================================
Identifier: your-unique-identifier
Server: http://0.0.0.0:8000
KEM Public Key: [your-kem-public-key]
Sign Public Key: [your-sign-public-key]
================================================================================
```

## Command Line Options

```bash
python -m zerotrace.main --help
```

Available options:

- `--host`: Server host address (default: 0.0.0.0)
- `--port`: Server port (default: 8000)
- `--data-dir`: Data directory for keys and database (default: current directory)
- `--server-only`: Run server without interactive CLI

### Server-Only Mode

To run just the server without the interactive menu:

```bash
python -m zerotrace.main --server-only --port 8000
```

This is useful for running nodes that just forward messages.

## Architecture

### Components

1. **SecureMessenger**: Handles encryption/decryption with post-quantum cryptography
2. **Database**: SQLite-based storage for messages, contacts, and routing history
3. **Kademlia DHT**: Distributed hash table for P2P networking
4. **FastAPI Server**: HTTP-based API for message routing

### Message Flow

1. **Sending**: Message → Encrypt with recipient's public key → Sign → Send to network
2. **Routing**: Message → Check if for this node → If not, forward to known contacts
3. **Receiving**: Message → Decrypt with private key → Verify signature → Store

### Security Features

- **Post-Quantum KEM**: ML-KEM (Kyber) for key encapsulation
- **Post-Quantum Signatures**: ML-DSA (Dilithium) for message signing
- **Symmetric Encryption**: AES-GCM for message content
- **Key Derivation**: HKDF for deriving encryption keys from shared secrets
- **Password Protection**: Scrypt for password-based key encryption

## Files and Data

The client creates several files in the data directory:

- `user_keys.json`: Encrypted private keys and public keys
- `zerotrace.db`: SQLite database for messages and contacts
- `kademlia.db`: SQLite database for DHT routing table

## Networking Multiple Nodes

To create a P2P network:

1. **Node 1** (Bootstrap node):
   ```bash
   python -m zerotrace.main --port 8000
   ```

2. **Node 2** (Connect to bootstrap):
   ```bash
   python -m zerotrace.main --port 8001 --data-dir ./node2
   ```
   
   Then add Node 1 as a contact to establish the connection.

3. **Node 3** and beyond: Same process, different ports and data directories

## Troubleshooting

### "Wrong Password"
- Make sure you're entering the correct password
- Keys are encrypted, wrong password = cannot decrypt

### "Contact not found"
- Add the contact first using option 3
- Verify the identifier is correct

### "Failed to send message"
- Check that the recipient's server is running
- Verify the contact's address is correct and reachable
- Check network connectivity

### Server won't start
- Port might be in use, try a different port with `--port`
- Check firewall settings

## Example Workflow

### Two-User Setup

**Alice (Node 1)**:
```bash
# Terminal 1
python -m zerotrace.main --port 8000 --data-dir ./alice
# Create password, get identifier and public keys
# Share identifier and public keys with Bob
```

**Bob (Node 2)**:
```bash
# Terminal 2
python -m zerotrace.main --port 8001 --data-dir ./bob
# Create password, get identifier and public keys
# Add Alice as contact (paste her info)
```

**Alice**:
```
# Add Bob as contact
# Send message to Bob
```

**Bob**:
```
# View messages to see Alice's message
# Reply to Alice
```

## Security Best Practices

1. **Password**: Use a strong, unique password
2. **Backup**: Keep a secure backup of `user_keys.json`
3. **Network**: Run behind a firewall if not intending to expose publicly
4. **Updates**: Keep dependencies updated for security patches
5. **Verification**: Verify contact public keys through a separate channel

## Advanced Usage

### Custom Database Location

```bash
python -m zerotrace.main --data-dir /path/to/secure/location
```

### Running on Public IP

```bash
python -m zerotrace.main --host 0.0.0.0 --port 8000
# Make sure firewall allows incoming connections on port 8000
```

### Integration with Other Services

The server exposes HTTP endpoints that can be called by other applications:

- `POST /send`: Send a message
- `POST /get_messages/{identifier}`: Get forwarded messages
- Plus Kademlia DHT endpoints

## Support

For issues, questions, or contributions, please refer to the project repository.

---

**ZeroTrace** - Secure P2P Messaging with Post-Quantum Cryptography
