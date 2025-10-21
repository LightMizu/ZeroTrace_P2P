# ZeroTrace Quick Start with I2P

## 🚀 Start ZeroTrace (Recommended Way)

### Windows

```bash
# Navigate to ZeroTrace directory
cd "c:\Users\InfSec-08\Documents\ZeroTrace\P2P TEST\zerotrace"

# Run ZeroTrace (auto-starts i2pd)
python -m zerotrace.main
```

Or double-click: **`start_zerotrace.bat`**

### What Happens

1. ✅ **i2pd router starts** automatically
2. ⏳ **Waits 10 seconds** for I2P initialization
3. 🔍 **Retrieves I2P destination** automatically
4. 📋 **Displays your .b32.i2p address**
5. 🎯 **ZeroTrace ready** to send/receive messages

## 📍 Getting Your I2P Destination

### Automatic Detection (Preferred)

ZeroTrace will try to get your destination automatically from:

1. **i2pd HTTP console** (http://127.0.0.1:7070)
2. **Keys file** (zerotrace.dat)

If successful, you'll see:

```
🎯 Found I2P destination from console:
   abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqr.b32.i2p
```

### Manual Entry (If Auto-detection Fails)

If auto-detection fails, follow the prompts:

```
📍 I2P Destination Address Required
================================================================

To find your I2P destination:
  1. Open i2pd console: http://127.0.0.1:7070
  2. Go to 'I2P Tunnels' page
  3. Find 'zerotrace-api' tunnel
  4. Copy the destination address (ends with .b32.i2p)

Enter your I2P destination address (.b32.i2p): 
```

**Steps:**

1. Open browser → http://127.0.0.1:7070
2. Click **"I2P Tunnels"**
3. Find **"zerotrace-api"** in the list
4. **Copy** the long address ending in `.b32.i2p`
5. **Paste** into terminal
6. Press Enter

## 🔧 Alternative: Manual I2P Start

If you prefer to control i2pd separately:

### Terminal 1: Start i2pd

```bash
.\i2pd.exe --tunconf .\tunnels.conf
```

**Wait** for message:
```
Tunnel created for [zerotrace-api]
```

### Terminal 2: Start ZeroTrace (without auto-start)

```bash
python -m zerotrace.main --no-i2p
```

⚠️ **Note**: Using `--no-i2p` disables automatic i2pd management but ZeroTrace will still try to connect through I2P proxy if i2pd is running externally.

## ✅ Verify Setup

After starting, use the menu to check your setup:

```
Select option: 5 (Show My Info)
```

You should see:

```
📋 Your Information:
================================================================================
Identifier: vYxG8h3kL9mN2pQ5r...
Server (Local): http://0.0.0.0:8000
Server (I2P): http://abcdefg...xyz.b32.i2p
I2P Status: ✅ Running
KEM Public Key: AAABAA...
Sign Public Key: AAABAA...
================================================================================
```

**Important fields:**
- ✅ **I2P Status**: Should show "✅ Running"
- ✅ **Server (I2P)**: Your .b32.i2p address

## 🌐 Share Your Address

To let others message you, share:

1. **Your Identifier**: Copy from "Your Information"
2. **Your I2P Destination**: The .b32.i2p address
3. **Your Public Keys**: KEM and Sign public keys

**Example:**

```
Add me on ZeroTrace:

Identifier: vYxG8h3kL9mN2pQ5r8tVwXy1z4A6cDeF
Address: http://abc...xyz.b32.i2p
KEM Public Key: AAABAA...
Sign Public Key: AAABAA...
```

## 📥 Add Contact Over I2P

When someone shares their ZeroTrace info:

1. Menu → **Option 3** (Add Contact)
2. Enter their details:
   - Name: Any friendly name
   - Identifier: Their identifier string
   - Address: **Their .b32.i2p address** (must be I2P address!)
   - KEM Public Key: Their key
   - Sign Public Key: Their key

**Example:**

```
➕ Add New Contact
Name: Alice
Identifier: xY9aB2cD3eF4gH5iJ...
Address: http://xyz...abc.b32.i2p  ← Must be .b32.i2p!
KEM Public Key: AAABAA...
Sign Public Key: AAABAA...
```

## 💬 Send Message Over I2P

```
Select option: 1 (Send Message)
Recipient ID: xY9aB2cD3eF4gH5iJ...
Message: Hello over I2P!

✅ Message saved to outbox
🔄 Attempting direct send...
✅ Message sent directly to Alice
```

**Note**: First I2P message may take 5-10 seconds. Subsequent messages are faster (~1-3 seconds).

## 🔍 Test I2P Connection

### Check i2pd is Running

**Windows:**
```cmd
tasklist | findstr i2pd
```

Should output:
```
i2pd.exe    12345 Console    1     25,000 K
```

### Check i2pd Console

Open browser: http://127.0.0.1:7070

Should show:
- ✅ **Status**: Running
- ✅ **Tunnels**: Active
- ✅ **Uptime**: Increasing

### Check Your Tunnel

In console → **I2P Tunnels** → Find **zerotrace-api**:

```
Name: zerotrace-api
Type: HTTP Server
Status: ✅ Active
Inbound: 3 hops
Outbound: 3 hops
Destination: abc...xyz.b32.i2p
```

## ⚙️ Command Line Options

```bash
# Default (auto-start i2pd on port 8000)
python -m zerotrace.main

# Custom port (update tunnels.conf too!)
python -m zerotrace.main --port 8001

# Custom data directory
python -m zerotrace.main --data-dir ./my_profile

# Disable auto-start i2pd (use manual start)
python -m zerotrace.main --no-i2p

# Custom i2pd path
python -m zerotrace.main --i2pd-path C:\i2p\i2pd.exe

# Custom tunnel config
python -m zerotrace.main --tunnels-conf my_tunnels.conf

# Server only (no interactive menu)
python -m zerotrace.main --server-only
```

## 🐛 Troubleshooting

### i2pd won't start

**Error**: `i2pd executable not found`

**Fix**:
```bash
# Check file exists
dir i2pd.exe

# If missing, verify you're in correct directory
cd "c:\Users\InfSec-08\Documents\ZeroTrace\P2P TEST\zerotrace"
```

### Can't find destination

**Issue**: Auto-detection fails

**Fix**:
1. Wait 15 seconds after i2pd starts
2. Check http://127.0.0.1:7070
3. Manually enter destination when prompted
4. Or: check `zerotrace.dat` was created

### Port 8000 in use

**Error**: `Address already in use`

**Fix**:
```bash
# Use different port
python -m zerotrace.main --port 8001

# Update tunnels.conf:
# port = 8001
```

### I2P console not accessible

**Fix**: Enable HTTP console

Create `i2pd.conf`:
```ini
[http]
enabled = true
address = 127.0.0.1
port = 7070
```

Restart i2pd

### Connection timeout

**Normal behavior**: I2P is slower than clearnet

- First connection: 5-10 seconds
- Subsequent: 1-3 seconds
- Be patient!

## 📂 Important Files

```
zerotrace/
├── i2pd.exe              ← I2P router binary
├── tunnels.conf          ← Tunnel configuration
├── zerotrace.dat         ← YOUR I2P KEYS (BACKUP!)
├── user_keys.json        ← Your ZeroTrace keys (BACKUP!)
├── zerotrace.db          ← Messages database
└── kademlia.db          ← DHT database
```

**BACKUP THESE FILES:**
- `zerotrace.dat` - Your persistent I2P destination
- `user_keys.json` - Your encryption keys

## 🔒 Security Notes

### ✅ With I2P

- Anonymous: IP address hidden
- Encrypted: End-to-end + transport layer
- Censorship-resistant: Distributed network
- Private: Location cannot be traced

### ❌ Without I2P (--no-i2p)

- **INSECURE**: Direct IP connections
- Your IP is **VISIBLE** to all contacts
- Only for **TESTING** on local network
- **NEVER** use for real privacy needs

## 🚨 Common Mistakes

### ❌ Wrong: Using clearnet address

```
Address: http://192.168.1.100:8000  ← WRONG! Leaks IP!
```

### ✅ Correct: Using I2P address

```
Address: http://abc...xyz.b32.i2p  ← RIGHT! Anonymous!
```

### ❌ Wrong: Forgetting to start i2pd

```
python -m zerotrace.main --no-i2p  ← Missing i2p flag!
# Then trying to use I2P addresses → Won't work!
```

### ✅ Correct: Let ZeroTrace manage i2pd

```
python -m zerotrace.main  ← Automatic i2pd startup
```

## 📚 Next Steps

1. ✅ **Start ZeroTrace** with I2P
2. ✅ **Get your I2P destination**
3. ✅ **Share** with contacts
4. ✅ **Add contacts** (use their .b32.i2p addresses!)
5. ✅ **Send messages** over I2P network
6. 📖 **Read**: I2P_SETUP.md for advanced configuration

## 🆘 Still Need Help?

1. **Check logs**: i2pd window for errors
2. **Test I2P**: Run `test_i2p.bat`
3. **Read full guide**: I2P_SETUP.md
4. **Verify network**: http://127.0.0.1:7070

---

**Ready?** → Run: `python -m zerotrace.main`
