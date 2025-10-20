# ZeroTrace CLI Messenger - Quick Reference

## Quick Start

```bash
# Start the messenger
python -m zerotrace.main

# With custom options
python -m zerotrace.main --port 8000 --data-dir ./data

# Server-only mode (no interactive CLI)
python -m zerotrace.main --server-only
```

## First Time Setup

1. Run the client
2. Create a password when prompted
3. Your keys will be generated and saved
4. Share your identifier and public keys with contacts

## Main Menu

```
1. Send Message         - Send encrypted message to a contact
2. View Messages        - View received messages
3. Add Contact          - Add new contact to address book
4. List Contacts        - Show all contacts
5. Show My Info         - Display your public information
6. Exit                 - Quit the application
```

## Adding Contacts

To exchange messages, you need to add contacts first:

1. Get their information (identifier, server address, public keys)
2. Select "Add Contact" from menu
3. Enter their details
4. Now you can send messages to them

## Sharing Your Info

Use "Show My Info" to get your details to share with others:
- Identifier (unique ID)
- Server address
- KEM Public Key
- Signature Public Key

## File Structure

```
data-dir/
├── user_keys.json      # Your encrypted private keys
├── zerotrace.db        # Messages and contacts database
└── kademlia.db         # P2P network routing table
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | 0.0.0.0 | Server host address |
| `--port` | 8000 | Server port number |
| `--data-dir` | . | Directory for data files |
| `--server-only` | false | Run without interactive menu |

## Security Features

- ✅ Post-Quantum Cryptography (ML-KEM, ML-DSA)
- ✅ End-to-End Encryption
- ✅ Digital Signatures
- ✅ Password-Protected Keys
- ✅ P2P Network (No Central Server)

## Example Workflow

### Setup Two Nodes

**Node 1 (Alice)**:
```bash
python -m zerotrace.main --port 8000 --data-dir ./alice
# Create account, note identifier and keys
```

**Node 2 (Bob)**:
```bash
python -m zerotrace.main --port 8001 --data-dir ./bob
# Create account, note identifier and keys
```

### Exchange Info & Message

1. Alice selects "Show My Info" and shares with Bob
2. Bob selects "Add Contact" and enters Alice's info
3. Alice adds Bob as contact too
4. Bob selects "Send Message", enters Alice's ID and message
5. Alice selects "View Messages" to see Bob's message

## Programmatic Usage

See `example_usage.py` for API examples:

```bash
python example_usage.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Wrong password | Re-enter correct password |
| Contact not found | Add contact first |
| Send failed | Check contact's server is running |
| Port in use | Use different port with `--port` |

## API Endpoints

The server exposes these HTTP endpoints:

- `POST /send` - Send message
- `POST /get_messages/{identifier}` - Get forwarded messages
- `GET /id` - Get node ID
- `POST /ping` - Ping node
- `POST /store` - Store value in DHT
- `POST /find_value` - Find value in DHT

## More Information

- Full documentation: `CLI_USAGE.md`
- Example code: `example_usage.py`
- Architecture: See main documentation

---

**ZeroTrace** - Secure P2P Messaging System
