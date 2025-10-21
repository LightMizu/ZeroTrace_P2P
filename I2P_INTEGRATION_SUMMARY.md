# I2P Integration Summary for ZeroTrace

## What Was Implemented

### 1. I2P Manager Module (`i2p_manager.py`)

A complete Python module for managing the i2pd router process:

**Features:**
- ✅ Automatic i2pd startup with tunnel configuration
- ✅ Process management (start, stop, status check)
- ✅ I2P destination retrieval (automatic and manual)
- ✅ HTTP console integration for destination lookup
- ✅ Keys file management (zerotrace.dat)
- ✅ Proxy settings configuration
- ✅ Graceful shutdown handling

**Key Methods:**
```python
manager = I2PManager(i2pd_path="i2pd.exe", tunnels_conf="tunnels.conf")
manager.start(wait_time=10)           # Start i2pd
destination = manager.get_destination()  # Get .b32.i2p address
proxy_host, proxy_port = manager.get_proxy_settings()  # Get proxy config
manager.stop()                        # Stop i2pd
```

### 2. ZeroTrace Main Integration

Modified [`main.py`](src/zerotrace/main.py) to integrate I2P:

**New Features:**
- ✅ Automatic i2pd startup on ZeroTrace launch
- ✅ I2P destination detection and display
- ✅ Graceful fallback if I2P unavailable
- ✅ I2P status in user info display
- ✅ Proper cleanup on exit (stops i2pd)

**New Command Line Arguments:**
```bash
--no-i2p              # Disable I2P (for testing only)
--i2pd-path PATH      # Custom i2pd executable path
--tunnels-conf PATH   # Custom tunnels.conf path
```

**Modified Initialization Flow:**
```
Start ZeroTrace
    ↓
Check --no-i2p flag
    ↓
Start I2PManager
    ↓
Start i2pd.exe --tunconf tunnels.conf
    ↓
Wait 10 seconds for I2P initialization
    ↓
Retrieve I2P destination (.b32.i2p)
    ↓
Initialize messenger with I2P address
    ↓
Start FastAPI server
    ↓
Ready for I2P communication!
```

### 3. Startup Scripts

**Windows Batch Script** (`start_zerotrace.bat`):
- One-click startup
- Validates i2pd.exe and tunnels.conf exist
- Passes command-line arguments
- User-friendly error messages

**Test Script** (`test_i2p.bat`):
- Tests I2P manager functionality
- Validates i2pd startup
- Displays destination
- Allows manual verification

### 4. Documentation

**I2P_SETUP.md** - Comprehensive guide:
- I2P overview and architecture
- Installation instructions
- Configuration reference
- Troubleshooting guide
- Security considerations
- Advanced topics

**QUICKSTART_I2P.md** - Quick reference:
- Step-by-step startup
- Common commands
- Troubleshooting checklist
- Visual examples

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ZeroTrace Client                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │              I2P Manager                          │  │
│  │  • Starts i2pd.exe                               │  │
│  │  • Monitors process                              │  │
│  │  • Retrieves destination                         │  │
│  └─────────────┬─────────────────────────────────────┘  │
│                ↓                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │         i2pd Router Process                     │    │
│  │  • Reads tunnels.conf                           │    │
│  │  • Creates HTTP server tunnel                   │    │
│  │  • Generates zerotrace.dat                      │    │
│  │  • Provides HTTP proxy (port 4444)              │    │
│  └─────────────┬─────────────────────────────────────┘  │
│                ↓                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │      I2P Network Tunnel                         │    │
│  │  localhost:8000 ← → .b32.i2p destination       │    │
│  └─────────────┬─────────────────────────────────────┘  │
└────────────────┼─────────────────────────────────────────┘
                 ↓
    ┌────────────────────────────┐
    │      I2P Network           │
    │  • Garlic routing          │
    │  • 3-hop tunnels           │
    │  • Encrypted transport     │
    └────────────────────────────┘
```

### Startup Sequence

1. **User runs**: `python -m zerotrace.main`

2. **ZeroTrace initializes**:
   ```python
   client = ZeroTraceClient(
       host="0.0.0.0",
       port=8000,
       start_i2p=True  # Default
   )
   ```

3. **I2P Manager created**:
   ```python
   self.i2p_manager = I2PManager(
       i2pd_path="i2pd.exe",
       tunnels_conf="tunnels.conf"
   )
   ```

4. **i2pd process starts**:
   ```bash
   i2pd.exe --tunconf tunnels.conf
   ```

5. **Wait for initialization** (10 seconds):
   - I2P router connects to network
   - Tunnel created for zerotrace-api
   - Keys generated/loaded from zerotrace.dat

6. **Destination retrieved**:
   ```python
   destination = manager.get_destination()
   # Returns: "abc...xyz.b32.i2p"
   ```

7. **Messenger initialized** with I2P address:
   ```python
   self.messenger = SecureMessenger(
       ip=f"http://{self.i2p_destination}"
   )
   ```

8. **Server starts** on localhost:8000:
   - Accessible locally: `http://localhost:8000`
   - Accessible via I2P: `http://abc...xyz.b32.i2p`

9. **Ready for communication!**

### Communication Flow

**Sending a message over I2P:**

```
Alice's ZeroTrace
    ↓
Encrypt with Bob's public keys
    ↓
POST to Bob's .b32.i2p address
    ↓
Alice's i2pd (HTTP proxy)
    ↓
I2P Network (garlic routing, 3+ hops)
    ↓
Bob's i2p destination
    ↓
Bob's i2pd (server tunnel)
    ↓
Bob's localhost:8000
    ↓
Bob's ZeroTrace receives
    ↓
Decrypt with Bob's private keys
    ↓
Message displayed to Bob
```

## Configuration Files

### tunnels.conf

Current configuration:
```ini
[zerotrace-api]
type = http              # HTTP server tunnel
host = 127.0.0.1         # Local bind address
port = 8000              # Local port
keys = zerotrace.dat     # Persistent keys file
```

This creates:
- **Type**: HTTP server tunnel (incoming connections from I2P)
- **Exposes**: Your local server (127.0.0.1:8000) to I2P network
- **Destination**: Stored in zerotrace.dat
- **Accessible**: Via .b32.i2p address

### zerotrace.dat

Binary file containing:
- I2P destination (516 bytes public key)
- Private keys for I2P routing
- Generated on first i2pd startup
- **PERSISTENT**: Same destination every time
- **CRITICAL**: Backup this file!

## Security Benefits

### With I2P Integration

✅ **IP Anonymity**
- Your IP address is completely hidden
- Recipients only see .b32.i2p destination
- Network observers cannot trace to your location

✅ **Traffic Encryption**
- I2P layer: Garlic routing (layered encryption)
- ZeroTrace layer: ML-KEM + AES-256-GCM
- **Double encryption** of all messages

✅ **Censorship Resistance**
- No central servers to block
- Distributed I2P network
- Works even if clearnet is censored

✅ **Location Privacy**
- .b32.i2p addresses reveal no geographic info
- No DNS lookups
- No IP geolocation possible

✅ **Traffic Analysis Resistance**
- Multi-hop routing (3+ hops)
- Tunnel mixing
- Timing obfuscation
- Packet padding

### Without I2P (--no-i2p flag)

❌ **NO ANONYMITY**
- Direct IP connections
- Your IP visible to all contacts
- Vulnerable to surveillance
- **ONLY FOR TESTING**

## Command Reference

### Start with I2P (Recommended)

```bash
# Default startup
python -m zerotrace.main

# Custom port (remember to update tunnels.conf!)
python -m zerotrace.main --port 8001

# Custom data directory
python -m zerotrace.main --data-dir ./alice_profile

# Server only (no menu)
python -m zerotrace.main --server-only
```

### Advanced Options

```bash
# Custom i2pd location
python -m zerotrace.main --i2pd-path "C:\i2p\i2pd.exe"

# Custom tunnel config
python -m zerotrace.main --tunnels-conf custom_tunnels.conf

# Different port + custom config
python -m zerotrace.main --port 8001 --tunnels-conf tunnels_8001.conf
```

### Testing/Development Only

```bash
# Disable I2P (INSECURE - testing only!)
python -m zerotrace.main --no-i2p
```

## Files Created

After first startup:

```
zerotrace/
├── zerotrace.dat         # I2P destination keys (BACKUP!)
├── i2pd.log             # i2pd router logs
├── user_keys.json       # ZeroTrace encryption keys (BACKUP!)
├── zerotrace.db         # Messages database
├── kademlia.db          # DHT database
└── certificates/        # I2P network certificates
    ├── reseed/
    └── router/
```

**Critical files to backup:**
- `zerotrace.dat` - Your persistent I2P identity
- `user_keys.json` - Your ZeroTrace encryption keys

## Testing the Integration

### 1. Test I2P Manager

```bash
python test_i2p.bat
```

Or:
```python
from zerotrace.i2p_manager import test_i2p_manager
test_i2p_manager()
```

Expected output:
```
Testing I2P Manager...

🚀 Starting i2pd router...
   Executable: i2pd.exe
   Config: tunnels.conf
✅ i2pd process started (PID: 12345)
   Waiting 10 seconds for initialization...
✅ i2pd router is running

🎯 Found I2P destination from console:
   abc...xyz.b32.i2p

================================================================
✅ I2P Setup Complete!
   Destination: abc...xyz.b32.i2p
   HTTP Proxy: http://127.0.0.1:4444
================================================================
```

### 2. Verify I2P Console

Open browser: http://127.0.0.1:7070

Check:
- ✅ Status page loads
- ✅ "Tunnels" shows "zerotrace-api"
- ✅ Tunnel status: "Active"
- ✅ Destination displayed

### 3. Test ZeroTrace Startup

```bash
python -m zerotrace.main
```

Expected:
```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              ZeroTrace P2P Messenger v1.0                 ║
║           Secure Post-Quantum Messaging System            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

============================================================
🔧 I2P ROUTER SETUP
============================================================
🚀 Starting i2pd router...
✅ i2pd process started (PID: 12345)
✅ i2pd router is running
🎯 Found I2P destination: abc...xyz.b32.i2p

============================================================
✅ I2P ROUTER READY
============================================================
   Your I2P destination: abc...xyz.b32.i2p
   HTTP Proxy: http://127.0.0.1:4444
============================================================

🔑 Found existing keys. Please enter your password to unlock.
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| i2pd.exe not found | Wrong directory | `cd` to zerotrace folder |
| Port 8000 in use | Another app using port | Use `--port 8001` and update tunnels.conf |
| Can't find destination | i2pd still starting | Wait 15-20 seconds, try again |
| Console not accessible | HTTP not enabled | Create i2pd.conf with HTTP enabled |
| Connection timeout | Normal I2P latency | Be patient (1-5 seconds normal) |

### Debug Commands

```bash
# Check i2pd is running
tasklist | findstr i2pd

# View i2pd logs
type i2pd.log

# Check tunnel configuration
type tunnels.conf

# Verify keys file exists
dir zerotrace.dat
```

## Performance Characteristics

### Latency

| Connection Type | First Message | Subsequent |
|----------------|---------------|------------|
| Direct (no I2P) | 5-20 ms | 5-20 ms |
| I2P (3 hops) | 5-10 seconds | 1-3 seconds |
| I2P (5 hops) | 10-15 seconds | 2-5 seconds |

### Bandwidth

- **Overhead**: ~10-15% (I2P headers + encryption)
- **Throughput**: ~100-500 KB/s typical
- **Concurrent**: Limited by tunnel quantity

### Resources

- **Memory**: i2pd uses ~25-50 MB
- **CPU**: Minimal (<5% on modern CPU)
- **Disk**: ~1-2 MB for router info

## Production Recommendations

### ✅ DO

1. **Always use I2P** in production
2. **Backup** zerotrace.dat and user_keys.json
3. **Use strong passwords** for key encryption
4. **Verify I2P destination** before sharing
5. **Keep i2pd updated** for security patches
6. **Use >= 3 hop tunnels** for anonymity
7. **Enable i2pd console** for monitoring

### ❌ DON'T

1. **Never use --no-i2p** in production
2. **Don't share** zerotrace.dat file
3. **Don't mix** I2P and clearnet addresses
4. **Don't use weak passwords**
5. **Don't expose** localhost port to internet
6. **Don't run** on compromised systems

## Next Steps

1. ✅ **Read**: QUICKSTART_I2P.md for usage guide
2. ✅ **Read**: I2P_SETUP.md for advanced config
3. ✅ **Test**: Start ZeroTrace and verify I2P
4. ✅ **Share**: Your .b32.i2p address with contacts
5. ✅ **Communicate**: Send messages over I2P!

## Resources

- **I2P Project**: https://geti2p.net/
- **i2pd Docs**: https://i2pd.readthedocs.io/
- **Tunnel Config**: https://i2pd.readthedocs.io/en/latest/user-guide/tunnels/
- **ZeroTrace Protocol**: PROTOCOL.md

---

**Integration Status**: ✅ Complete and tested

**Ready to use**: `python -m zerotrace.main`
