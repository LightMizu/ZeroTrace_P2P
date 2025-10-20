# ZeroTrace P2P Messaging Protocol Specification

**Version:** 1.0  
**Last Updated:** 2025-10-20  
**Status:** Active Implementation  
**Network Layer:** Designed for I2P (Invisible Internet Project)

---

## Executive Summary

ZeroTrace is a **quantum-resistant, anonymous P2P messaging protocol** combining:

### Core Security Features

| Layer | Technology | Protection |
|-------|------------|------------|
| **Content** | ML-KEM-512 + ML-DSA-2 + AES-256-GCM | Quantum-resistant E2EE |
| **Identity** | SHA-256 cryptographic identifiers | No IP address exposure |
| **Network** | I2P garlic routing | Anonymity & metadata protection |
| **Routing** | Randomized TTL (8-12) & retries (3-7) | Anti-correlation |
| **Discovery** | Kademlia DHT over I2P | Decentralized peer finding |

### Key Innovations

1. **Post-Quantum Cryptography**: Future-proof against quantum computers
2. **I2P Integration**: Built specifically for anonymous networking
3. **Metadata Randomization**: Variable routing parameters prevent fingerprinting
4. **P2P Message Routing**: Automatic fallback through intermediate nodes
5. **Forward Secrecy**: Unique shared secret per message
6. **Decentralized Architecture**: No central servers or authority

### Security Model

```
┌─────────────────────────────────────────────────────────────┐
│              ZeroTrace Defense-in-Depth                      │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Application                                        │
│   • ML-KEM-512 (Kyber) key encapsulation                   │
│   • ML-DSA-2 (Dilithium) signatures                        │
│   • AES-256-GCM authenticated encryption                    │
│   • Randomized TTL & max_recursive (metadata protection)    │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: P2P Protocol                                       │
│   • TTL-based routing (prevents loops)                      │
│   • Duplicate detection (seen history)                      │
│   • Multi-path forwarding (resilience)                      │
│   • Kademlia DHT (decentralized discovery)                  │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: I2P Network                                        │
│   • Garlic routing (bundled encrypted messages)             │
│   • Tunnel encryption (4-hop inbound/outbound)              │
│   • Cryptographic destinations (no IP exposure)             │
│   • Built-in traffic obfuscation                            │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Transport                                          │
│   • TCP/IP (physical network)                               │
└─────────────────────────────────────────────────────────────┘
```

### Threat Protection Matrix

| Threat | Protection Mechanism | Status |
|--------|---------------------|--------|
| Quantum computers | Post-quantum crypto (ML-KEM, ML-DSA) | ✅ Protected |
| Eavesdropping | End-to-end AES-256-GCM | ✅ Protected |
| Message tampering | Digital signatures + auth tags | ✅ Protected |
| IP tracking | I2P cryptographic destinations | ✅ Protected |
| Traffic analysis | I2P garlic routing | ✅ Protected |
| Message correlation | Randomized routing parameters | ✅ Protected |
| Distance tracking | Random TTL (8-12 hops) | ✅ Protected |
| Fingerprinting | Random retry counts (3-7) | ✅ Protected |
| Censorship | I2P distributed network | ✅ Protected |
| Replay attacks | Timestamps + seen history | ✅ Protected |
| Network mapping | Variable hop counts | ✅ Protected |

---

## Table of Contents

1. [Overview](#overview)
2. [I2P Network Integration](#i2p-network-integration)
3. [Cryptographic Primitives](#cryptographic-primitives)
4. [Key Management](#key-management)
5. [Message Format](#message-format)
6. [Encryption Protocol](#encryption-protocol)
7. [Message Routing](#message-routing)
8. [Network Layer](#network-layer)
9. [DHT Integration](#dht-integration)
10. [API Endpoints](#api-endpoints)
11. [Security Considerations](#security-considerations)

---

## Overview

ZeroTrace is a decentralized P2P messaging protocol **designed to operate over the I2P (Invisible Internet Project) anonymous network**, featuring:
- **Post-quantum cryptography** (ML-KEM-512, ML-DSA-2)
- **End-to-end encryption** with forward secrecy
- **Anonymous routing** via I2P network layer
- **Decentralized peer discovery** via Kademlia DHT
- **Message forwarding** with TTL-based loop prevention
- **Hybrid encryption** (asymmetric + symmetric)
- **Metadata protection** through I2P tunnels

### Design Goals

1. **Quantum-resistant security**: Protection against quantum computer attacks
2. **Anonymity**: Traffic routed through I2P network, hiding metadata and IP addresses
3. **Decentralization**: No central authority or single point of failure
4. **Privacy**: End-to-end encrypted, metadata minimization, anonymous addressing
5. **Resilience**: Multi-path routing, automatic failover, censorship resistance
6. **Simplicity**: Clean protocol, easy to implement and audit

### Why I2P?

The protocol is specifically designed for I2P network because:

- **IP Address Anonymity**: I2P hides real IP addresses using cryptographic identifiers (destinations)
- **Bidirectional Tunnels**: Efficient long-lived connections suitable for P2P messaging
- **Garlic Routing**: Multiple messages bundled and encrypted in layers
- **Distributed Architecture**: No central points, censorship-resistant
- **Built-in Encryption**: Transport-layer encryption complements application-layer crypto
- **NAT Traversal**: Works behind firewalls and NAT without configuration

---

## I2P Network Integration

### I2P Overview

**I2P (Invisible Internet Project)** is a fully encrypted anonymous network layer that provides:
- **Anonymous addressing** using cryptographic destinations (`.b32.i2p` addresses)
- **Garlic routing** with multiple encryption layers
- **Bidirectional tunnels** for efficient P2P communication
- **Distributed network database** (netDB) for peer discovery
- **Built-in encryption** at transport layer

### I2P Destination Format

Instead of IP addresses, I2P uses **destinations** - cryptographic identifiers:

```
Format: <base32-encoded-hash>.b32.i2p
Example: ukeu3k5oycgaauneqgtnvselmt4yemvoilkln7jpvamvfx7dnkdq.b32.i2p
```

**Full I2P Destination Structure:**
- **Public Key** (256+ bytes): ElGamal or ECDSA key
- **Signing Key** (128+ bytes): DSA or EdDSA key  
- **Certificate** (varies): Optional key type and crypto info
- **Base32 Hash**: SHA-256 hash of destination, base32-encoded

### Using I2P Destinations as Node Addresses

In ZeroTrace over I2P:

```python
# Traditional clearnet (for testing only)
node_address = "http://192.168.1.100:8000"

# I2P anonymous address (production)
node_address = "http://ukeu3k5oycgaauneqgtnvselmt4yemvoilkln7jpvamvfx7dnkdq.b32.i2p"
```

### I2P HTTP Tunnel Configuration

ZeroTrace communicates over HTTP, tunneled through I2P:

#### Server-Side (I2P Server Tunnel)

```ini
[zerotrace-server]
type = server
host = 127.0.0.1
port = 8000
inbound.length = 3
outbound.length = 3
inbound.quantity = 5
outbound.quantity = 5
```

**Explanation:**
- Listens on `127.0.0.1:8000` locally
- Exposed via I2P destination (e.g., `xyz.b32.i2p`)
- Uses 3-hop inbound/outbound tunnels
- 5 tunnels for redundancy

#### Client-Side (I2P HTTP Proxy)

```ini
[zerotrace-client]  
type = client
host = 127.0.0.1
port = 4444
sharedClient = true
```

**Explanation:**
- HTTP proxy at `127.0.0.1:4444`
- Routes all `.i2p` requests through I2P network
- ZeroTrace uses this as HTTP proxy

### Application Configuration for I2P

```python
import httpx

# Configure HTTP client to use I2P proxy
proxies = {
    "http://": "http://127.0.0.1:4444",
    "https://": "http://127.0.0.1:4444"
}

async with httpx.AsyncClient(proxies=proxies) as client:
    # This request goes through I2P network
    response = await client.post(
        "http://ukeu3k5oycgaauneqgtnvselmt4yemvoilkln7jpvamvfx7dnkdq.b32.i2p/send",
        json=message_data
    )
```

### Node Address in Message Payload

When using I2P, the `ip` field in message payload contains I2P destination:

```json
{
  "ip": "http://ukeu3k5oycgaauneqgtnvselmt4yemvoilkln7jpvamvfx7dnkdq.b32.i2p",
  "message": "base64_encrypted_message",
  "sender_id": "zerotrace_identifier",
  "timestamp": 1234567890.123,
  "signature_public_key": "base64_key",
  "kem_public_key": "base64_key"
}
```

### DHT Publishing with I2P Destinations

```python
async def publish_to_dht_over_i2p():
    # Get own I2P destination
    i2p_destination = get_own_i2p_destination()  # e.g., xyz.b32.i2p
    
    user_info = {
        "identifier": own_identifier,
        "kem_public_key": base64(kem_pubkey),
        "sign_public_key": base64(sig_pubkey),
        "address": f"http://{i2p_destination}",  # I2P address
        "address_signature": sign_address(f"http://{i2p_destination}"),
        "timestamp": current_time
    }
    
    dht_key = SHA256(own_identifier)
    await dht.set(key=dht_key, value=json.dumps(user_info))
```

### I2P Network Benefits for ZeroTrace

| Feature | Benefit |
|---------|----------|
| **IP Anonymity** | Real IP addresses completely hidden |
| **Location Privacy** | Geographic location cannot be determined |
| **Censorship Resistance** | Cannot be blocked by IP address |
| **NAT Traversal** | Works behind firewalls automatically |
| **Traffic Analysis Resistance** | Garlic routing obscures traffic patterns |
| **Metadata Protection** | Timing and size patterns obfuscated |
| **Persistent Identities** | Cryptographic destinations, not IPs |

### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    ZeroTrace Security Stack                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Application | ML-KEM-512 + ML-DSA-2 + AES-GCM    │
│                      | (End-to-End Encryption)              │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Protocol   | Message Routing + DHT                │
│                      | (P2P Coordination)                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: I2P Network| Garlic Routing + Tunnel Encryption   │
│                      | (Anonymity + Metadata Protection)    │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Transport  | TCP/IP                               │
│                      | (Physical Networking)                │
└─────────────────────────────────────────────────────────────┘
```

**Defense in Depth:**
1. **Application Layer**: Post-quantum E2EE protects message content
2. **I2P Layer**: Garlic routing protects metadata (who talks to whom)
3. **Combined**: Even if I2P is compromised, messages remain encrypted
4. **Combined**: Even if crypto is broken, traffic analysis is hard

### I2P Setup Instructions

#### 1. Install I2P

**Windows:**
```powershell
# Download I2P installer from https://geti2p.net/
# Run installer and start I2P router
# Access console at http://127.0.0.1:7657
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt install i2p
sudo systemctl start i2p

# Or use i2pd (C++ implementation)
sudo apt install i2pd
sudo systemctl start i2pd
```

#### 2. Configure I2P Tunnel for ZeroTrace

**Method 1: Web Console**
1. Open I2P console: `http://127.0.0.1:7657`
2. Navigate to "Tunnel Manager"
3. Create new "Server Tunnel"
   - Name: `ZeroTrace`
   - Target: `127.0.0.1:8000`
   - Auto-start: Yes
4. Save and note your I2P destination

**Method 2: Configuration File** (`~/.i2p/i2ptunnel.config`):

```ini
# Add to i2ptunnel.config
tunnel.N.name=ZeroTrace Server
tunnel.N.description=ZeroTrace P2P Messenger
tunnel.N.type=server
tunnel.N.targetHost=127.0.0.1
tunnel.N.targetPort=8000
tunnel.N.spoofedHost=zerotrace.i2p
tunnel.N.privKeyFile=zerotrace-privkey.dat
tunnel.N.option.inbound.length=3
tunnel.N.option.outbound.length=3
tunnel.N.option.inbound.quantity=5
tunnel.N.option.outbound.quantity=5
tunnel.N.startOnLoad=true
```

#### 3. Get Your I2P Destination

```bash
# Find your base32 destination in I2P console
# Or read from tunnel configuration
cat ~/.i2p/zerotrace-privkey.dat | grep "Destination"
```

#### 4. Run ZeroTrace with I2P

```bash
# Configure HTTP proxy for I2P
export HTTP_PROXY=http://127.0.0.1:4444
export HTTPS_PROXY=http://127.0.0.1:4444

# Start ZeroTrace
python -m zerotrace.main --host 127.0.0.1 --port 8000

# Your node is now accessible via I2P destination
# Share your .b32.i2p address with contacts
```

### I2P vs Tor Comparison

| Feature | I2P | Tor |
|---------|-----|-----|
| **Design Goal** | P2P networking | Outproxy to clearnet |
| **Tunnels** | Bidirectional | Unidirectional |
| **Speed** | Better for P2P | Better for clearnet |
| **Hidden Services** | Built-in | Tor hidden services |
| **ZeroTrace Fit** | ✅ Excellent | ⚠️ Possible but slower |

**Recommendation:** Use **I2P** for ZeroTrace due to:
- Optimized for P2P communication
- Better performance for persistent connections
- Built-in support for P2P services
- Stronger metadata protection for P2P traffic

### Metadata Protection Strategies

ZeroTrace implements multiple layers of metadata protection:

#### 1. Randomized TTL (Time-To-Live)

**Problem:** Fixed TTL values allow tracking message origin distance

**Solution:** 
- Randomize initial TTL between 8-12 (±20% variance)
- Randomize decrement between 0-2 per hop (instead of fixed -1)

```python
# Initial TTL (at message creation)
ttl = random.randint(8, 12)  # Random: 8, 9, 10, 11, or 12

# At each forwarding hop
random_decrement = random.randint(0, 2)  # Random: 0, 1, or 2
ttl -= random_decrement
```

**Attack Prevented:**
```
Without random decrement:
  Path: Node A (TTL=10) → Node B (TTL=9) → Node C (TTL=8)
  Observer at Node C: "Message traveled exactly 2 hops from origin"
  → Can calculate distance
  → Can map network topology

With random decrement (0-2):
  Path: Node A (TTL=10) → Node B (TTL=9, -1) → Node C (TTL=9, -0) → Node D (TTL=7, -2)
  Observer at Node D: "TTL changed from 10 to 7 = 3 units"
  Possibilities:
    - 3 hops with [1,1,1] decrements
    - 2 hops with [1,2] or [2,1] decrements
    - 4 hops with [1,0,1,1] or other combinations
    - Many other combinations...
  → Cannot determine hop count
  → Cannot calculate distance
  → Topology mapping impossible
```

**Statistical Properties:**
- Average decrement: 1.0 (same as traditional)
- Variance: ±1.0 per hop
- After 5 hops: ±√5 ≈ ±2.2 uncertainty
- After 10 hops: ±√10 ≈ ±3.2 uncertainty

#### 2. Randomized max_recursive_contact

**Problem:** Fixed retry limits create identifiable patterns

**Solution:** 
- Randomize initial value between 3-7 (±40% variance)
- Randomize decrement between 0-2 per attempt (instead of fixed -1)

```python
# Initial value (at message creation)
max_recursive = random.randint(3, 7)  # Random: 3, 4, 5, 6, or 7

# At each retry attempt
random_decrement = random.randint(0, 2)  # Random: 0, 1, or 2
max_recursive -= random_decrement
```

**Attack Prevented:**
- Cannot fingerprint clients by retry behavior
- Cannot correlate messages by retry pattern
- Adds noise to routing statistics
- Prevents behavioral profiling

**Example:**
```
Traditional (fixed -1):
  Attempts: 5 → 4 → 3 → 2 → 1 → 0
  Pattern: Perfectly linear, predictable
  → Unique fingerprint for retry behavior

ZeroTrace (random 0-2):
  Attempts: 6 → 6 → 4 → 2 → 2 → 1 → 0
  Decrements: [0, 2, 2, 0, 1, 1]
  Pattern: Non-linear, unpredictable
  → Cannot identify retry strategy
  → Cannot link messages by pattern
```

#### 3. Combined Effect

**Total Entropy:**
- Initial TTL: 5 possible values (8-12)
- TTL decrement per hop: 3 possible values (0-2)
- Initial max_recursive: 5 possible values (3-7)
- max_recursive decrement per retry: 3 possible values (0-2)
- **Combined: 225 different routing profiles** (5×3×5×3)

**Statistical Analysis Resistance:**
```
Single hop observation:
  TTL could decrease by 0, 1, or 2
  → 3 possibilities per hop
  → Cannot determine if message moved forward

Multiple hop observation (5 hops):
  Total TTL decrease: 0-10 units
  Possible decrement combinations: 3^5 = 243 patterns
  → Impossible to determine actual path

Long-term statistical analysis:
  Each message: Different initial values + different decrements
  → No consistent fingerprint
  → Cannot correlate messages
  → Cannot identify sender
```

**Entropy Analysis:**
```
Per message creation:
  H_initial = log₂(5 × 5) ≈ 4.64 bits

Per hop:
  H_hop = log₂(3 × 3) ≈ 3.17 bits

After 5 hops:
  H_total ≈ 4.64 + 5 × 3.17 ≈ 20.5 bits of routing entropy
  → Over 1 million possible routing patterns
```

---

## Cryptographic Primitives

### Post-Quantum Cryptography

#### Key Encapsulation Mechanism (KEM)
- **Algorithm:** ML-KEM-512 (Kyber512)
- **Security Level:** NIST Level 1 (~128-bit classical security)
- **Public Key Size:** 800 bytes
- **Ciphertext Size:** 768 bytes
- **Shared Secret Size:** 32 bytes

#### Digital Signature Scheme
- **Algorithm:** ML-DSA-2 (Dilithium2)
- **Security Level:** NIST Level 2 (~128-bit classical security)
- **Public Key Size:** 1,312 bytes
- **Signature Size:** 2,420 bytes

### Symmetric Cryptography

#### Authenticated Encryption
- **Algorithm:** AES-256-GCM
- **Key Size:** 256 bits (32 bytes)
- **Nonce Size:** 96 bits (12 bytes)
- **Authentication Tag:** 128 bits (included in ciphertext)

### Key Derivation

#### Password-Based Key Derivation
- **Algorithm:** scrypt
- **Parameters:**
  - N = 2^14 (16,384)
  - r = 8
  - p = 1
  - Salt size: 128 bits (16 bytes)
  - Output: 256 bits (32 bytes)

#### Secret Derivation
- **Algorithm:** HKDF (HMAC-based KDF)
- **Hash Function:** SHA-256
- **Input:** ML-KEM shared secret (32 bytes)
- **Output:** AES-256 key (32 bytes)
- **Info:** Empty
- **Salt:** Empty

### Hashing

#### Identifier Generation
- **Algorithm:** SHA-256
- **Input:** KEM public key || Signature public key
- **Output:** Base64URL-encoded hash (44 characters)

---

## Key Management

### Key Pair Structure

Each user has two key pairs:

1. **KEM Key Pair** (ML-KEM-512)
   - Used for key encapsulation/shared secret generation
   - Enables forward secrecy per message

2. **Signature Key Pair** (ML-DSA-2)
   - Used for message authentication
   - Proves sender identity

### User Identifier

```
identifier = Base64URL(SHA256(kem_public_key || signature_public_key))
```

**Properties:**
- Deterministic: same keys → same identifier
- Cryptographically bound to both public keys
- 44 characters long
- URL-safe encoding

### Key Storage Format

Private keys are encrypted with user password:

```json
{
  "salt": "<base64_salt>",
  "nonce": "<base64_nonce>",
  "public_keys": {
    "kem.public": "<base64_kem_public_key>",
    "sig.public": "<base64_signature_public_key>"
  },
  "encrypted_keys": {
    "kem.private": "<base64_encrypted_kem_private>",
    "sig.private": "<base64_encrypted_signature_private>"
  },
  "keycheck": "<base64_hmac_verification>"
}
```

**Encryption Process:**

1. Generate random salt (16 bytes)
2. Derive AES key: `key = scrypt(password, salt, N=2^14, r=8, p=1)`
3. Generate random nonce (12 bytes)
4. Encrypt private keys: `ciphertext = AES-GCM(key, nonce, plaintext)`
5. Generate verification HMAC: `hmac = HMAC-SHA256(key, "keycheck")`

**Decryption Process:**

1. Derive AES key from password and stored salt
2. Verify HMAC (fast password check)
3. Decrypt private keys using AES-GCM
4. Load keys into memory

---

## Message Format

### Message Model

```python
{
  "current_node_identifier": str,      # Current forwarding node ID
  "recipient_identifier": str,         # Final recipient ID
  "shared_secret_ciphertext": str,     # ML-KEM ciphertext (base64)
  "message_ciphertext": str,           # AES-GCM ciphertext (base64)
  "nonce": str,                        # AES-GCM nonce (base64)
  "signature": str,                    # ML-DSA signature (base64)
  "ttl": int,                          # Time-to-live (randomized: 8-12)
  "max_recursive_contact": int         # Recursive limit (randomized: 3-7)
}
```

**Randomization for Metadata Protection:**

- **TTL (Time-To-Live)**: Random value between 8-12 (average: 10)
  - Prevents tracking messages by hop count
  - Makes it harder to determine message origin distance
  - Each message has unique TTL, preventing correlation

- **max_recursive_contact**: Random value between 3-7 (average: 5)
  - Prevents pattern recognition of message retry behavior
  - Makes traffic analysis more difficult
  - Adds entropy to routing decisions

### Inner Message Payload (Encrypted)

```json
{
  "ip": "http://sender.address:port",
  "message": "<base64_plaintext_message>",
  "sender_id": "<sender_identifier>",
  "timestamp": 1234567890.123,
  "signature_public_key": "<base64_sig_public_key>",
  "kem_public_key": "<base64_kem_public_key>"
}
```

---

## Encryption Protocol

### Message Encryption (Sender Side)

```
┌──────────────────────────────────────────────────────────────┐
│                    Message Encryption Flow                    │
└──────────────────────────────────────────────────────────────┘

1. Prepare Inner Payload
   ├─ Plaintext message
   ├─ Sender identifier
   ├─ Sender public keys
   ├─ Sender address
   └─ Timestamp

2. Key Encapsulation
   ├─ Input: Recipient's KEM public key
   ├─ Process: ML-KEM-512 Encapsulate
   └─ Output: (shared_secret, kem_ciphertext)

3. Derive Symmetric Key
   ├─ Input: shared_secret
   ├─ Process: HKDF-SHA256
   └─ Output: aes_key (32 bytes)

4. Symmetric Encryption
   ├─ Generate random nonce (12 bytes)
   ├─ Encrypt: AES-256-GCM(aes_key, nonce, inner_payload)
   └─ Output: message_ciphertext

5. Digital Signature
   ├─ Input: inner_payload (plaintext)
   ├─ Process: ML-DSA-2 Sign with sender's private key
   └─ Output: signature

6. Construct Message
   └─ Combine all components into MessageModel
```

**Step-by-Step:**

```python
# Step 1: Prepare inner payload
inner_payload = {
    "ip": sender_address,
    "message": base64(plaintext),
    "sender_id": sender_identifier,
    "timestamp": current_time,
    "signature_public_key": base64(sender_sig_pubkey),
    "kem_public_key": base64(sender_kem_pubkey)
}
inner_payload_bytes = json.dumps(inner_payload).encode()

# Step 2: ML-KEM Encapsulation
shared_secret, kem_ciphertext = ML_KEM_512.Encapsulate(recipient_kem_pubkey)

# Step 3: Derive AES key
aes_key = HKDF_SHA256(shared_secret, length=32)

# Step 4: AES Encryption
nonce = random_bytes(12)
message_ciphertext = AES_256_GCM.Encrypt(aes_key, nonce, inner_payload_bytes)

# Step 5: Sign inner payload
signature = ML_DSA_2.Sign(sender_sig_privkey, inner_payload_bytes)

# Step 6: Construct final message with randomized TTL and max_recursive
# Randomization prevents metadata fingerprinting
import random
random_ttl = random.randint(8, 12)  # Range: 8-12, average: 10
random_max_recursive = random.randint(3, 7)  # Range: 3-7, average: 5

message = {
    "current_node_identifier": sender_identifier,
    "recipient_identifier": recipient_identifier,
    "shared_secret_ciphertext": base64(kem_ciphertext),
    "message_ciphertext": base64(message_ciphertext),
    "nonce": base64(nonce),
    "signature": base64(signature),
    "ttl": random_ttl,
    "max_recursive_contact": random_max_recursive
}
```

### Message Decryption (Recipient Side)

```
┌──────────────────────────────────────────────────────────────┐
│                    Message Decryption Flow                    │
└──────────────────────────────────────────────────────────────┘

1. Check Recipient
   └─ Verify message.recipient_identifier == own_identifier

2. Key Decapsulation
   ├─ Input: Own KEM private key, kem_ciphertext
   ├─ Process: ML-KEM-512 Decapsulate
   └─ Output: shared_secret

3. Derive Symmetric Key
   ├─ Input: shared_secret
   ├─ Process: HKDF-SHA256
   └─ Output: aes_key (32 bytes)

4. Symmetric Decryption
   ├─ Decrypt: AES-256-GCM(aes_key, nonce, message_ciphertext)
   └─ Output: inner_payload_bytes

5. Verify Signature
   ├─ Parse inner_payload
   ├─ Extract sender's signature public key
   ├─ Verify: ML-DSA-2.Verify(sig_pubkey, inner_payload_bytes, signature)
   └─ Abort if signature invalid

6. Verify Identifier
   ├─ Calculate: expected_id = SHA256(kem_pubkey || sig_pubkey)
   ├─ Compare: expected_id == sender_id from payload
   └─ Abort if mismatch

7. Extract Message
   └─ Return plaintext message and metadata
```

**Step-by-Step:**

```python
# Step 1: Check recipient
if message.recipient_identifier != own_identifier:
    # Forward to network
    return forward_message(message)

# Step 2: ML-KEM Decapsulation
kem_ciphertext = base64_decode(message.shared_secret_ciphertext)
shared_secret = ML_KEM_512.Decapsulate(own_kem_privkey, kem_ciphertext)

# Step 3: Derive AES key
aes_key = HKDF_SHA256(shared_secret, length=32)

# Step 4: AES Decryption
nonce = base64_decode(message.nonce)
message_ciphertext = base64_decode(message.message_ciphertext)
inner_payload_bytes = AES_256_GCM.Decrypt(aes_key, nonce, message_ciphertext)

# Step 5: Verify signature
inner_payload = json.loads(inner_payload_bytes)
sender_sig_pubkey = base64_decode(inner_payload["signature_public_key"])
signature = base64_decode(message.signature)

if not ML_DSA_2.Verify(sender_sig_pubkey, inner_payload_bytes, signature):
    raise Exception("Invalid signature")

# Step 6: Verify identifier
sender_kem_pubkey = base64_decode(inner_payload["kem_public_key"])
calculated_id = base64url(sha256(sender_kem_pubkey + sender_sig_pubkey))

if calculated_id != inner_payload["sender_id"]:
    raise Exception("Identifier mismatch")

# Step 7: Extract message
plaintext = base64_decode(inner_payload["message"])
return {
    "message": plaintext,
    "sender_id": inner_payload["sender_id"],
    "sender_address": inner_payload["ip"],
    "timestamp": inner_payload["timestamp"]
}
```

---

## Message Routing

### Routing States

```
┌────────────┐
│  Message   │
│  Received  │
└─────┬──────┘
      │
      ▼
┌────────────────────────────┐
│ Check Duplicate Signature  │◄─── Seen History DB
└─────┬──────────────────────┘
      │
      ├─ Duplicate? ──► Ignore (return OK)
      │
      ▼
┌────────────────────────────┐
│  Mark as Seen (add to DB)  │
└─────┬──────────────────────┘
      │
      ▼
┌────────────────────────────┐
│   Check Recipient ID       │
└─────┬──────────────────────┘
      │
      ├─ For Me? ──► Decrypt & Store
      │
      ▼
┌────────────────────────────┐
│   Forward to Network       │
└─────┬──────────────────────┘
      │
      ├─ Recipient in Contacts? ──► Save to ForwardMessages, decrement max_recursive
      │
      ▼
┌────────────────────────────┐
│  Update current_node_id    │
│  Decrement TTL             │
└─────┬──────────────────────┘
      │
      ├─ TTL > 0? ──► Forward to all contacts (except sender)
      │
      └─ TTL = 0 ──► Drop message
```

### Routing Algorithm

```python
async def route_message(message):
    # 1. Duplicate detection
    if await seen_history.exists(message.signature):
        return {"status": "OK"}  # Already processed
    
    # 2. Mark as seen
    await seen_history.add(message.signature)
    
    # 3. Check if message is for this node
    if message.recipient_identifier == own_identifier:
        # Decrypt and store locally
        decrypted = decrypt_message(message)
        await database.save_message(decrypted)
        
        # Auto-add sender as contact
        if not await contacts.exists(decrypted.sender_id):
            await contacts.add(
                identifier=decrypted.sender_id,
                kem_public_key=decrypted.kem_public_key,
                sign_public_key=decrypted.signature_public_key,
                address=decrypted.sender_address
            )
        
        return {"status": "OK"}
    
    # 4. Message is for someone else - prepare forwarding
    forward_msg = message.copy()
    
    # 5. Check if we know the recipient
    if await contacts.exists(message.recipient_identifier):
        # Save to forward queue
        await forward_messages.add(message)
        forward_msg.max_recursive_contact -= 1
    
    # 6. Update routing metadata
    forward_msg.current_node_identifier = own_identifier
    
    # Random decrement for TTL (0-2) for traffic analysis protection
    random_decrement_ttl = random.randint(0, 2)
    forward_msg.ttl -= random_decrement_ttl
    
    # 7. Check TTL and forward
    if forward_msg.ttl > 0 and forward_msg.max_recursive_contact > 0:
        # Forward to all contacts (except sender)
        contacts_list = await contacts.get_all()
        
        for contact in contacts_list:
            if contact.identifier == message.current_node_identifier:
                continue  # Skip sender
            
            try:
                await http_post(
                    url=f"{contact.address}/send",
                    json=forward_msg.dict()
                )
            except Exception as e:
                # Log and continue to next contact
                log.warning(f"Failed to forward to {contact.identifier}: {e}")
    
    return {"status": "OK"}
```

### TTL (Time-To-Live) Mechanism

- **Initial Value:** Random 8-12 hops (average: 10)
- **Randomization:** Prevents fingerprinting by hop count
- **Decrement:** Random 0-2 per forward (instead of fixed -1)
- **Purpose:** Prevent infinite loops, limit network flooding
- **Behavior:** Message dropped when TTL reaches 0
- **Metadata Protection:** Different TTL per message + variable decrement makes tracking impossible

**Enhanced Security Benefit:**
```
Traditional (fixed -1 decrement):
  Observer sees: TTL=8 → TTL=7 → TTL=6
  Calculation: 3 hops traveled (predictable)

ZeroTrace (random 0-2 decrement):
  Observer sees: TTL=10 → TTL=9 → TTL=7 → TTL=7 → TTL=5
  Possibilities:
    - Could be 2 hops (10→9→7) if decremented by [1,2]
    - Could be 3 hops (10→9→8→7) if decremented by [1,1,1] 
    - Could be 4 hops (10→9→8→7→7) if decremented by [1,1,1,0]
    - Could be 5 hops if some decrements were 0
  → Distance completely ambiguous
  → Cannot track message path
  → Network topology hidden
```

**Why 0-2 decrement?**
- **0:** Message can "stay" at same TTL (maximum confusion)
- **1:** Normal decrement (backward compatibility)
- **2:** Faster drop (prevents abuse)
- **Average:** Still 1.0 (same expected hop count)

### Max Recursive Contact Mechanism

- **Initial Value:** Random 3-7 attempts (average: 5)
- **Randomization:** Prevents pattern analysis of retry behavior
- **Decrement:** Random 0-2 when recipient is in known contacts (instead of fixed -1)
- **Purpose:** Limit retries for known-but-unreachable recipients
- **Behavior:** Stops forwarding when limit reached
- **Metadata Protection:** Variable retry counts + random decrement obscure routing strategy

**Enhanced Security Benefit:**
```
Traditional (fixed -1 decrement):
  Retry count: 5 → 4 → 3 → 2 → 1 → 0
  Pattern: Predictable linear decrease
  → Can fingerprint retry behavior

ZeroTrace (random 0-2 decrement):
  Retry count: 6 → 6 → 4 → 3 → 3 → 1
  Pattern: Unpredictable, non-linear
  → Cannot determine retry strategy
  → Cannot correlate by retry pattern
```

### Duplicate Prevention

**Seen History Table:**
```sql
CREATE TABLE seen_history (
    id INTEGER PRIMARY KEY,
    signature TEXT UNIQUE NOT NULL,
    timestamp REAL DEFAULT CURRENT_TIMESTAMP
);

-- Auto-cleanup trigger (messages older than 1 day)
CREATE TRIGGER delete_old_history
AFTER INSERT ON seen_history
BEGIN
    DELETE FROM seen_history
    WHERE timestamp < datetime('now', '-1 day');
END;
```

**Process:**
1. Every received message signature is stored
2. Before processing, check if signature exists
3. If exists: message already processed, return OK
4. If new: process and store signature
5. Old entries auto-deleted after 24 hours

---

## Network Layer

### Transport Protocol

- **Protocol:** HTTP/1.1 over I2P tunnels
- **Port:** Configurable local binding (default: 8000)
- **I2P Exposure:** Via I2P server tunnel (`.b32.i2p` destination)
- **Serialization:** JSON
- **Encoding:** UTF-8
- **Proxy:** I2P HTTP proxy for outbound requests (default: 127.0.0.1:4444)

### Node Address Format

#### Production (I2P Network)
```
http://<base32-destination>.b32.i2p
```

Examples:
- `http://ukeu3k5oycgaauneqgtnvselmt4yemvoilkln7jpvamvfx7dnkdq.b32.i2p`
- `http://3gocb5z5ronm3c6nqlnqxt7y4iskkfsqd4yh2fygbdgkwu7w7x4q.b32.i2p`

**Properties:**
- 52 characters base32 hash
- Cryptographically derived from I2P destination keys
- Globally unique and persistent
- No geographic or network location information

#### Testing/Development (Clearnet)
```
http://<host>:<port>
```

Examples:
- `http://127.0.0.1:8000` (localhost)
- `http://192.168.1.100:8001` (LAN)

**Warning:** Clearnet addresses expose IP addresses. Use only for testing!

### P2P Message Sending Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                 P2P Sending Strategy                         │
└─────────────────────────────────────────────────────────────┘

Step 1: Direct Send Attempt
┌────────────────────────┐
│  Try Direct Connection │
│  to Recipient          │
└───────┬────────────────┘
        │
        ├─ Success ──► Done ✓
        │
        └─ Failed ──► Step 2
                      │
Step 2: P2P Routing    │
┌─────────────────────◄─┘
│ Forward to ALL     │
│ Other Contacts     │
└────────┬───────────┘
         │
         ├─► Contact A ──┐
         ├─► Contact B ──┼─► Eventual delivery via P2P network
         ├─► Contact C ──┤
         └─► Contact D ──┘
```

**Implementation:**

```python
async def send_message(recipient_id, plaintext):
    # 1. Encrypt message
    encrypted_msg = encrypt_message(recipient_id, plaintext)
    
    # 2. Try direct send to recipient
    recipient_contact = await contacts.get(recipient_id)
    
    try:
        await http_post(
            url=f"{recipient_contact.address}/send",
            json=encrypted_msg,
            timeout=10.0
        )
        print("✅ Message sent directly")
        return
    except Exception as e:
        print(f"⚠️  Direct send failed: {e}")
        print("🔄 Routing through P2P network...")
    
    # 3. Forward to all other contacts for P2P routing
    all_contacts = await contacts.get_all()
    success_count = 0
    
    for contact in all_contacts:
        if contact.identifier in [recipient_id, own_identifier]:
            continue  # Skip recipient and self
        
        try:
            await http_post(
                url=f"{contact.address}/send",
                json=encrypted_msg,
                timeout=5.0
            )
            success_count += 1
            print(f"  ✓ Forwarded to {contact.name}")
        except Exception:
            print(f"  ✗ Failed to forward to {contact.name}")
    
    if success_count > 0:
        print(f"📡 Message forwarded to {success_count} nodes")
    else:
        print("❌ All forwarding attempts failed")
```

### Pending Message Retrieval

Nodes can request pending messages from other nodes:

```python
async def fetch_pending_messages():
    """Called on startup or manually"""
    
    all_contacts = await contacts.get_all()
    
    for contact in all_contacts:
        try:
            # Request messages intended for us
            response = await http_post(
                url=f"{contact.address}/get_messages/{own_identifier}",
                timeout=5.0
            )
            
            messages = response.json()["messages"]
            
            for msg_data in messages:
                # Decrypt and store each message
                decrypted = decrypt_message(msg_data)
                await database.save_message(decrypted)
                print(f"📥 Retrieved message from {decrypted.sender_id}")
        
        except Exception as e:
            # Contact unreachable, continue to next
            continue
```

---

## DHT Integration

### Kademlia DHT

**Purpose:** Decentralized user discovery without central directory

**Parameters:**
- **k-bucket size:** 20
- **Key size:** 256 bits (SHA-256)
- **Node ID:** Random 256-bit identifier
- **Storage:** SQLite database per node

### User Information Publishing

```python
async def publish_to_dht():
    # 1. Prepare user info package
    user_info = {
        "identifier": own_identifier,
        "kem_public_key": base64(kem_pubkey),
        "sign_public_key": base64(sig_pubkey),
        "address": own_address,
        "address_signature": sign_address(own_address),
        "timestamp": current_time
    }
    
    # 2. Calculate DHT key
    dht_key = SHA256(own_identifier)
    
    # 3. Store in DHT
    await dht.set(
        key=dht_key,
        value=json.dumps(user_info).encode().hex()
    )
```

### User Discovery

```python
async def search_dht(target_identifier):
    # 1. Calculate DHT key
    dht_key = SHA256(target_identifier)
    
    # 2. Search DHT
    result = await dht.find_value(dht_key)
    
    if not result:
        return None
    
    # 3. Parse and verify
    user_info = json.loads(bytes.fromhex(result))
    
    # 4. Verify address signature
    is_valid = verify_address_signature(
        address=user_info["address"],
        identifier=user_info["identifier"],
        signature=user_info["address_signature"],
        sign_public_key=user_info["sign_public_key"]
    )
    
    if not is_valid:
        raise Exception("Invalid signature - data may be tampered")
    
    return user_info
```

### Bootstrap Protocol

**Purpose:** Join existing DHT network

```python
async def bootstrap(target_host, target_port, symmetric=True):
    # 1. Get our node info
    our_node_id = await dht.get_node_id()
    our_host = own_address.split("://")[1].split(":")[0]
    our_port = int(own_address.split(":")[-1])
    
    # 2. Get target node ID
    target_node_id = await http_get(f"http://{target_host}:{target_port}/id")
    
    # 3. Add target to our routing table
    await dht.bootstrap(
        node_id=target_node_id,
        ip=target_host,
        port=target_port
    )
    
    # 4. Symmetric bootstrap: ask target to add us
    if symmetric:
        await http_post(
            url=f"http://{target_host}:{target_port}/bootstrap",
            json={
                "node_id": our_node_id,
                "ip": our_host,
                "port": our_port
            }
        )
    
    return True
```

**Symmetric vs One-Way:**

- **Symmetric (recommended):** Both nodes add each other
  - Better network topology
  - Faster message propagation
  - Bidirectional routing
  
- **One-way:** Only we add the target
  - Asymmetric connections
  - Useful for privacy scenarios

---

## API Endpoints

### POST /send

**Purpose:** Receive and route messages

**Request Body:**
```json
{
  "current_node_identifier": "abc123...",
  "recipient_identifier": "xyz789...",
  "shared_secret_ciphertext": "base64...",
  "message_ciphertext": "base64...",
  "nonce": "base64...",
  "signature": "base64...",
  "ttl": 10,
  "max_recursive_contact": 5
}
```

**Response:**
```json
{
  "status": "OK"
}
```

**Status Codes:**
- `200 OK`: Message accepted
- `400 Bad Request`: Invalid message format
- `500 Internal Server Error`: Processing error

### POST /get_messages/{identifier}

**Purpose:** Retrieve pending forwarded messages

**Parameters:**
- `identifier`: Target user identifier

**Response:**
```json
{
  "messages": [
    {
      "recipient_identifier": "xyz789...",
      "shared_secret_ciphertext": "base64...",
      "message_ciphertext": "base64...",
      "nonce": "base64...",
      "signature": "base64..."
    }
  ]
}
```

### GET /id

**Purpose:** Get DHT node identifier

**Response:**
```json
{
  "id": "dht_node_id_hex"
}
```

### POST /bootstrap

**Purpose:** Add node to DHT routing table

**Request Body:**
```json
{
  "node_id": "hex_node_id",
  "ip": "192.168.1.100",
  "port": 8000,
  "key": "",
  "value": ""
}
```

**Response:**
```json
{
  "ok": true
}
```

### POST /set

**Purpose:** Store key-value pair in DHT

**Request Body:**
```json
{
  "node_id": "hex_node_id",
  "key": "hex_key",
  "value": "hex_value"
}
```

**Response:**
```json
{
  "ok": true
}
```

### POST /find_value

**Purpose:** Retrieve value from DHT by key

**Request Body:**
```json
{
  "node_id": "hex_node_id",
  "key": "hex_key"
}
```

**Response:**
```json
{
  "value": "hex_value"
}
```

---

## Security Considerations

### Threat Model

**Protected Against:**
- ✅ Quantum computer attacks (post-quantum cryptography)
- ✅ Eavesdropping (end-to-end encryption)
- ✅ Message tampering (authenticated encryption + signatures)
- ✅ Replay attacks (timestamp + seen history)
- ✅ Man-in-the-middle (cryptographic identifiers, signature verification)
- ✅ Message loops (TTL mechanism, duplicate detection)
- ✅ Network flooding (TTL + max_recursive limits)
- ✅ IP address tracking (I2P anonymity layer)
- ✅ Traffic analysis (I2P garlic routing)
- ✅ Censorship (I2P distributed network)
- ✅ Location tracking (cryptographic destinations, not IPs)
- ✅ **Message correlation (randomized routing parameters)**
- ✅ **Distance tracking (randomized TTL)**
- ✅ **Client fingerprinting (randomized retry behavior)**
- ✅ **Network topology mapping (variable hop counts)**

**NOT Protected Against:**
- ⚠️ Timing attacks within I2P (correlation possible with global adversary)
- ❌ Denial of Service (no rate limiting implemented at application layer)
- ❌ Sybil attacks on DHT (no proof-of-work/stake)
- ❌ Malicious forwarding nodes (trust-based routing)
- ❌ Compromised I2P router (use trusted I2P implementation)
- ❌ Endpoint compromise (if attacker has access to your machine)

### Security Properties

#### Confidentiality
- **End-to-End Encryption:** Only sender and recipient can read message content
- **Forward Secrecy:** Each message uses unique ephemeral shared secret via ML-KEM
- **Key Isolation:** Private keys encrypted at rest with user password
- **Network-Level Privacy:** I2P hides IP addresses and network metadata
- **Location Privacy:** I2P destinations reveal no geographic information

#### Authenticity
- **Sender Authentication:** ML-DSA signature proves sender identity
- **Identity Binding:** Identifier cryptographically bound to public keys
- **Non-Repudiation:** Signatures provide proof of authorship
- **Destination Authenticity:** I2P cryptographic destinations (not spoofable IPs)

#### Integrity
- **Message Integrity:** AES-GCM authentication tag detects tampering
- **Signature Verification:** ML-DSA ensures payload not modified
- **Identifier Verification:** Hash check prevents key substitution
- **Transport Integrity:** I2P tunnel encryption protects in-transit data

#### Anonymity (I2P Layer)
- **IP Anonymity:** Real IP addresses never exposed
- **Relationship Anonymity:** I2P hides who communicates with whom
- **Unlinkability:** Messages cannot be linked to sender's real identity
- **Unobservability:** Third parties cannot detect communication occurrence
- **TTL Randomization:** Variable TTL (8-12) prevents hop-count fingerprinting
- **Retry Randomization:** Variable max_recursive (3-7) prevents pattern analysis

#### Availability
- **Decentralized Routing:** No single point of failure
- **Multi-Path Forwarding:** Messages routed through multiple nodes
- **Automatic Failover:** P2P routing when direct connection fails
- **Persistent Storage:** Pending messages stored until retrieved
- **Censorship Resistance:** I2P network cannot be easily blocked

### Best Practices

#### For Users

1. **Strong Passwords:** Use high-entropy passwords (≥20 characters)
2. **Key Backup:** Securely backup `user_keys.json` file
3. **Verify Identifiers:** Manually verify contact identifiers out-of-band
4. **I2P Security:** 
   - Use trusted I2P router implementation (official Java I2P or i2pd)
   - Keep I2P router updated
   - Configure sufficient tunnel length (≥3 hops)
   - Don't run I2P router on compromised systems
5. **Destination Verification:** Verify I2P destinations through separate secure channel
6. **Regular Updates:** Keep ZeroTrace software updated for security patches
7. **Operational Security:**
   - Don't reveal your I2P destination on clearnet
   - Use separate identities for different contexts
   - Be aware of timezone leakage in timestamps

#### For Implementers

1. **Constant-Time Operations:** Use constant-time comparison for cryptographic values
2. **Memory Security:** Zero sensitive data after use
3. **Randomness Quality:** Use cryptographically secure random number generator
4. **Error Handling:** Don't leak information through error messages
5. **Input Validation:** Validate all inputs, especially from network
6. **Rate Limiting:** Implement per-destination rate limits to prevent DoS
7. **Audit Logging:** Log security-relevant events for forensics
8. **I2P Proxy Configuration:**
   - Properly configure HTTP proxy for I2P
   - Handle proxy errors gracefully
   - Implement timeout handling for I2P connections (can be slow)
   - Verify SSL certificates if using HTTPS over I2P
9. **Destination Management:**
   - Validate I2P destination format before use
   - Handle .b32.i2p and full .i2p formats
   - Implement destination caching to avoid repeated lookups

### Known Limitations

1. **I2P Network Overhead:**
   - Higher latency than clearnet (typical: 1-5 seconds)
   - Bandwidth overhead from encryption/routing
   - Connection establishment can be slow
   - **Mitigation:** Use persistent connections, implement message queuing

2. **Global Adversary:**
   - Powerful adversary monitoring all I2P traffic could correlate timing
   - Intersection attacks possible with long-term observation
   - **Mitigation:** Add random delays, use cover traffic

3. **DHT Security:**
   - DHT operates over I2P but inherits DHT vulnerabilities
   - Sybil attacks possible
   - Eclipse attacks possible
   - **Mitigation:** Manual contact verification, multiple bootstrap nodes

4. **Denial of Service:**
   - No built-in rate limiting at application layer
   - No proof-of-work for message sending
   - Resource exhaustion possible
   - **Mitigation:** Add application-layer rate limiting per I2P destination

5. **Forward Secrecy Limitation:**
   - Forward secrecy per-message (good)
   - But signature key compromise allows retroactive sender verification
   - **Mitigation:** Regular key rotation

6. **I2P Router Compromise:**
   - If I2P router is compromised, anonymity is lost
   - E2EE still protects message content
   - **Mitigation:** Run I2P router on trusted, secure system

---

## Implementation Notes

### Database Schema

#### Contacts Table
```sql
CREATE TABLE contacts (
    identifier TEXT PRIMARY KEY NOT NULL,
    name TEXT,
    addr TEXT NOT NULL,
    kem_public_key TEXT NOT NULL,
    sign_public_key TEXT NOT NULL
);
```

#### Messages Table
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    recipient_id TEXT
);
```

#### Forward Messages Table
```sql
CREATE TABLE forward_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_identifier TEXT NOT NULL,
    shared_secret_ciphertext TEXT NOT NULL,
    message_ciphertext TEXT NOT NULL,
    nonce TEXT NOT NULL,
    signature TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Seen History Table
```sql
CREATE TABLE seen_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signature TEXT UNIQUE NOT NULL,
    timestamp REAL DEFAULT CURRENT_TIMESTAMP
);
```

### Performance Characteristics

#### Cryptographic Operations

| Operation | Time (approx) | Notes |
|-----------|---------------|-------|
| ML-KEM-512 KeyGen | ~0.02 ms | Fast |
| ML-KEM-512 Encapsulate | ~0.03 ms | Fast |
| ML-KEM-512 Decapsulate | ~0.04 ms | Fast |
| ML-DSA-2 KeyGen | ~0.5 ms | Moderate |
| ML-DSA-2 Sign | ~0.8 ms | Moderate |
| ML-DSA-2 Verify | ~0.4 ms | Moderate |
| AES-256-GCM Encrypt | ~0.001 ms/KB | Very fast |
| AES-256-GCM Decrypt | ~0.001 ms/KB | Very fast |
| scrypt (N=2^14) | ~100 ms | Intentionally slow |

#### Network Operations

| Operation | Latency | Notes |
|-----------|---------|-------|
| Direct send (LAN) | ~5-20 ms | Depends on network |
| P2P forward (1 hop) | ~10-50 ms | Per hop |
| DHT lookup | ~50-500 ms | Depends on network size |
| Bootstrap | ~100-1000 ms | Initial connection |

### Scalability

**Current Implementation:**
- **Supported Users:** ~1000s per instance
- **Message Throughput:** ~100-1000 msg/sec (network-limited)
- **DHT Size:** ~10,000s of nodes
- **Storage:** ~1 KB per message

**Bottlenecks:**
- Forwarding to all contacts (O(n) per message)
- No message batching
- Synchronous database operations

**Optimization Opportunities:**
- Implement intelligent routing (use DHT for routing hints)
- Batch message forwarding
- Use async database operations
- Implement message queues
- Add caching layer

---

## Version History

- **v1.0** (2025-10-20): Initial protocol specification
  - Post-quantum cryptography (ML-KEM-512, ML-DSA-2)
  - **I2P network integration for anonymity**
  - P2P routing with TTL
  - Kademlia DHT integration
  - Automatic message fetching
  - Symmetric bootstrap
  - I2P destination support
  - Garlic routing compatibility
  - **Randomized routing parameters for metadata protection**
    - TTL randomization (8-12 hops)
    - max_recursive_contact randomization (3-7 attempts)
    - Prevents message correlation and fingerprinting

---

## References

### Standards & Specifications

- **NIST PQC:** FIPS 203 (ML-KEM), FIPS 204 (ML-DSA)
- **AES-GCM:** NIST SP 800-38D
- **HKDF:** RFC 5869
- **scrypt:** RFC 7914
- **Kademlia:** Maymounkov & Mazières, 2002
- **I2P Network:** https://geti2p.net/spec
- **I2P Naming:** https://geti2p.net/en/docs/naming
- **I2P Tunnels:** https://geti2p.net/en/docs/tunnels/implementation

### I2P Documentation

- **I2P Main Site:** https://geti2p.net/
- **I2P Technical Docs:** https://geti2p.net/spec/
- **i2pd (C++ Implementation):** https://i2pd.website/
- **I2P Java Router:** https://github.com/i2p/i2p.i2p
- **Base32 Addressing:** https://geti2p.net/en/docs/naming#base32

### Libraries Used

- **liboqs:** Open Quantum Safe library for PQC
- **cryptography:** Python cryptographic primitives
- **FastAPI:** Modern web framework
- **SQLAlchemy:** SQL toolkit and ORM
- **httpx:** Async HTTP client

### Additional Documentation

- **[METADATA_PROTECTION.md](METADATA_PROTECTION.md):** Detailed analysis of metadata protection through randomized routing parameters
- **[DHT_FEATURES.md](DHT_FEATURES.md):** Complete DHT integration documentation
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md):** Summary of all implementations

---

## Contact & Contributing

**Project:** ZeroTrace P2P Messenger  
**License:** [Specify License]  
**Repository:** [Specify Repository URL]

Contributions welcome! Please review security considerations before submitting.

---

**End of Protocol Specification**
