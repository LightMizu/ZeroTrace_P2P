# I2P Integration Guide for ZeroTrace

## Overview

ZeroTrace integrates with I2P (Invisible Internet Project) to provide network-level anonymity. All communication is routed through I2P's anonymous overlay network using cryptographic destinations instead of IP addresses.

## Prerequisites

### 1. I2P Router (i2pd)

You already have `i2pd.exe` in your project directory. This is the C++ implementation of I2P router.

**Alternative: Java I2P**
- Download from: https://geti2p.net/
- More features but requires Java Runtime

### 2. Tunnel Configuration

The `tunnels.conf` file is already configured with:

```ini
[zerotrace-api]
type = http
host = 127.0.0.1
port = 8000
keys = zerotrace.dat
```

This creates an I2P tunnel that:
- Exposes your local server (127.0.0.1:8000) to I2P network
- Generates a persistent I2P destination in `zerotrace.dat`
- Type: HTTP server tunnel

## Quick Start

### Method 1: Automatic (Recommended)

Simply run ZeroTrace - it will start i2pd automatically:

```bash
python -m zerotrace.main
```

Or use the batch script:

```bash
start_zerotrace.bat
```

### Method 2: Manual I2P Start

If you prefer to start i2pd manually:

```bash
# Terminal 1: Start i2pd
.\i2pd.exe --tunconf .\tunnels.conf

# Terminal 2: Start ZeroTrace without auto-starting i2pd
python -m zerotrace.main --no-i2p
```

## Getting Your I2P Destination

After starting i2pd, you need your I2P destination address (ends with `.b32.i2p`).

### Option 1: Automatic Detection

ZeroTrace will try to automatically detect your I2P destination from:
1. i2pd HTTP console (http://127.0.0.1:7070)
2. Reading the keys file

### Option 2: Manual Lookup

1. **Open i2pd console**: http://127.0.0.1:7070
2. **Navigate to**: "I2P Tunnels" page
3. **Find**: "zerotrace-api" tunnel
4. **Copy**: The destination address (52 characters + `.b32.i2p`)

Example destination:
```
abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqr.b32.i2p
```

### Option 3: Check i2pd Logs

Look at the i2pd console window for messages like:
```
Tunnel created for zerotrace-api
Destination: abcdefg...xyz.b32.i2p
```

## How It Works

### 1. Starting i2pd

When ZeroTrace starts with I2P enabled:

```python
# Automatic process
i2pd.exe --tunconf tunnels.conf
  ↓
Creates tunnel from localhost:8000 → I2P network
  ↓
Generates/loads destination from zerotrace.dat
  ↓
Your server is now accessible via .b32.i2p address
```

### 2. I2P Destination

Your I2P destination is a **cryptographic identifier**, not an IP address:

- **Length**: 52 characters (base32 encoded)
- **Format**: `[a-z2-7]{52}.b32.i2p`
- **Persistent**: Same destination every time (stored in zerotrace.dat)
- **Anonymous**: Does not reveal your IP address

### 3. Communication Flow

```
Alice (via I2P)  →  I2P Network  →  Bob's .b32.i2p  →  Bob's localhost:8000
                ↑                                    ↑
            Encrypted tunnels                 Your ZeroTrace server
            Multi-hop routing
            IP anonymity
```

## Command Line Options

```bash
# Start with default settings (auto-start i2pd)
python -m zerotrace.main

# Custom port
python -m zerotrace.main --port 8001

# Custom i2pd path
python -m zerotrace.main --i2pd-path C:\i2p\i2pd.exe

# Custom tunnels config
python -m zerotrace.main --tunnels-conf my_tunnels.conf

# Disable I2P (NOT RECOMMENDED for production)
python -m zerotrace.main --no-i2p
```

## Troubleshooting

### Issue: i2pd won't start

**Check:**
1. Is i2pd.exe in the current directory?
2. Is tunnels.conf present?
3. Is port 8000 already in use?

**Solution:**
```bash
# Use different port
python -m zerotrace.main --port 8001

# Update tunnels.conf to match:
# port = 8001
```

### Issue: Can't find I2P destination

**Check:**
1. Wait 10-15 seconds after i2pd starts
2. Check zerotrace.dat file exists
3. Open http://127.0.0.1:7070 in browser

**Solution:**
```bash
# ZeroTrace will prompt for manual entry
# Enter destination from i2pd console
```

### Issue: I2P console not accessible

**Enable in i2pd:**

Create or edit `i2pd.conf`:
```ini
[http]
enabled = true
address = 127.0.0.1
port = 7070
```

### Issue: Connection timeout

I2P connections can be slow (1-5 seconds is normal):

- First connection: ~5-10 seconds
- Subsequent: ~1-3 seconds
- Be patient with I2P network

## Security Considerations

### ✅ With I2P Enabled

- **IP Anonymity**: Your IP address is hidden
- **Location Privacy**: Geographic location obscured
- **Traffic Analysis Resistance**: Encrypted tunnels, garlic routing
- **Censorship Resistance**: Distributed network

### ❌ Without I2P (--no-i2p flag)

- **INSECURE**: Direct IP connections
- **NO ANONYMITY**: Your IP is visible
- **Only for testing**: Never use in production
- **Local network only**: Use behind firewall

## Files Created

```
zerotrace/
├── i2pd.exe              # I2P router binary
├── tunnels.conf          # Tunnel configuration
├── zerotrace.dat         # Your I2P keys (BACKUP THIS!)
├── i2pd.log             # i2pd logs (auto-generated)
└── certificates/         # I2P network certificates (auto-generated)
```

**Important**: Backup `zerotrace.dat` - it contains your persistent I2P destination!

## Advanced Configuration

### Multiple Tunnels

Edit `tunnels.conf` to add more tunnels:

```ini
[zerotrace-api]
type = http
host = 127.0.0.1
port = 8000
keys = zerotrace.dat

[zerotrace-dht]
type = http
host = 127.0.0.1
port = 8001
keys = zerotrace-dht.dat
```

### Tunnel Quantity

Increase anonymity (slower) or decrease for speed:

```ini
[zerotrace-api]
type = http
host = 127.0.0.1
port = 8000
keys = zerotrace.dat
inbound.length = 3     # Tunnel hops (default: 3)
outbound.length = 3
inbound.quantity = 5   # Parallel tunnels (default: 5)
outbound.quantity = 5
```

## Resources

- **I2P Website**: https://geti2p.net/
- **i2pd Documentation**: https://i2pd.readthedocs.io/
- **I2P Tunnel Types**: https://i2pd.readthedocs.io/en/latest/user-guide/tunnels/
- **I2P Network Status**: http://127.0.0.1:7070 (after starting i2pd)

## Testing I2P Connection

### 1. Check i2pd is running

```bash
# Windows
tasklist | findstr i2pd

# Should show: i2pd.exe
```

### 2. Check HTTP console

Open browser: http://127.0.0.1:7070

Should see i2pd status page

### 3. Check your tunnel

In i2pd console → I2P Tunnels → Find "zerotrace-api"

Should show:
- Status: Active
- Destination: [your .b32.i2p address]

### 4. Test with ZeroTrace

```bash
python -m zerotrace.main
# Select option 5: Show My Info
# Should display I2P destination
```

## FAQ

**Q: Why is I2P slower than direct connections?**

A: I2P routes through 3+ hops for anonymity. This adds latency (typically 1-5 seconds) but provides strong privacy guarantees.

**Q: Can I use the same destination on multiple machines?**

A: No. Each zerotrace.dat file is unique. Copy the file to use same destination elsewhere.

**Q: Is my I2P destination truly anonymous?**

A: Yes. I2P destinations are cryptographic identifiers with no link to your IP address or physical location.

**Q: What happens if i2pd crashes?**

A: ZeroTrace will continue running but won't be accessible via I2P. Restart i2pd to restore connectivity.

**Q: Can I access clearnet from ZeroTrace?**

A: No. ZeroTrace only communicates over I2P network. This is by design for security.

---

**Need Help?**

Check the ZeroTrace documentation or I2P community forums:
- https://geti2p.net/en/get-involved
- Reddit: r/i2p
