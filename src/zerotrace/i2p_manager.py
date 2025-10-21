#!/usr/bin/env python3
"""I2P Router Management for ZeroTrace"""

import os
import subprocess
import time
import re
from pathlib import Path
from typing import Optional, Tuple


class I2PManager:
    """Manage i2pd router process and I2P destination"""
    
    def __init__(self, i2pd_path: str = "i2pd.exe", tunnels_conf: str = "tunnels.conf"):
        self.i2pd_path = Path(i2pd_path)
        self.tunnels_conf = Path(tunnels_conf)
        self.process: Optional[subprocess.Popen] = None
        self.destination: Optional[str] = None
        self.keys_file = Path("zerotrace.dat")
        
        # Validate files exist
        if not self.i2pd_path.exists():
            raise FileNotFoundError(f"i2pd executable not found: {self.i2pd_path}")
        if not self.tunnels_conf.exists():
            raise FileNotFoundError(f"tunnels.conf not found: {self.tunnels_conf}")
    
    def start(self, wait_time: int = 5) -> bool:
        """Start i2pd router with tunnel configuration.
        
        Args:
            wait_time: Seconds to wait for i2pd to start
            
        Returns:
            True if started successfully
        """
        if self.process and self.process.poll() is None:
            print("⚠️  i2pd is already running")
            return True
        
        print(f"🚀 Starting i2pd router...")
        print(f"   Executable: {self.i2pd_path}")
        print(f"   Config: {self.tunnels_conf}")
        
        try:
            # Start i2pd with tunnel configuration
            # Using CREATE_NEW_CONSOLE to run in separate window
            self.process = subprocess.Popen(
                [str(self.i2pd_path), "--tunconf", str(self.tunnels_conf)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                cwd=str(self.i2pd_path.parent)
            )
            
            print(f"✅ i2pd process started (PID: {self.process.pid})")
            print(f"   Waiting {wait_time} seconds for initialization...")
            time.sleep(wait_time)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                print(f"❌ i2pd process terminated unexpectedly")
                if stderr:
                    print(f"   Error: {stderr.decode()}")
                return False
            
            print("✅ i2pd router is running")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start i2pd: {e}")
            return False
    
    def get_destination(self) -> Optional[str]:
        """Read I2P destination from keys file.
        
        Returns:
            Base32 I2P destination address (.b32.i2p) or None
        """
        if not self.keys_file.exists():
            print(f"⚠️  Keys file not found: {self.keys_file}")
            print(f"   i2pd should generate it automatically after startup")
            
            # Wait a bit more and check again
            print(f"   Waiting for keys file generation...")
            for i in range(10):
                time.sleep(1)
                if self.keys_file.exists():
                    print(f"   ✅ Keys file appeared after {i+1} seconds")
                    break
            else:
                print(f"   ❌ Keys file still not found after 10 seconds")
                return None
        
        try:
            # Read the keys file
            with open(self.keys_file, 'rb') as f:
                keys_data = f.read()
            
            # The .dat file is binary, but we can extract destination
            # For base32 address, we need to derive it from the destination
            # For now, inform user to check i2pd logs
            
            print(f"✅ Keys file found: {self.keys_file} ({len(keys_data)} bytes)")
            print(f"\n📝 To get your I2P destination address:")
            print(f"   1. Check i2pd console output")
            print(f"   2. Look for 'New tunnel created' or 'Destination' message")
            print(f"   3. The address will end with .b32.i2p")
            
            # Alternative: read from i2pd HTTP console if available
            destination = self._get_destination_from_console()
            if destination:
                self.destination = destination
                return destination
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to read keys file: {e}")
            return None
    
    def _get_destination_from_console(self) -> Optional[str]:
        """Try to get destination from i2pd HTTP console.
        
        Returns:
            I2P destination or None
        """
        try:
            import httpx
            
            # i2pd console usually runs on http://127.0.0.1:7070
            console_url = "http://127.0.0.1:7070"
            
            with httpx.Client(timeout=2.0) as client:
                # Try to get SAM sessions page which shows destinations
                resp = client.get(f"{console_url}/?page=i2p_tunnels")
                
                if resp.status_code == 200:
                    # Parse HTML to find destination
                    # Look for .b32.i2p addresses
                    html = resp.text
                    b32_pattern = r'([a-z2-7]{52})\.b32\.i2p'
                    matches = re.findall(b32_pattern, html)
                    
                    if matches:
                        # Look for zerotrace tunnel
                        for line in html.split('\n'):
                            if 'zerotrace' in line.lower():
                                match = re.search(b32_pattern, line)
                                if match:
                                    destination = f"{match.group(1)}.b32.i2p"
                                    print(f"\n🎯 Found I2P destination from console:")
                                    print(f"   {destination}")
                                    return destination
                        
                        # Return first match if zerotrace not specifically found
                        if matches:
                            destination = f"{matches[0]}.b32.i2p"
                            print(f"\n🎯 Found I2P destination (first tunnel):")
                            print(f"   {destination}")
                            return destination
        
        except Exception as e:
            # Silent fail - console might not be enabled
            pass
        
        return None
    
    def get_destination_manual(self) -> str:
        """Get destination address manually from user.
        
        Returns:
            I2P destination entered by user
        """
        print("\n" + "="*60)
        print("📍 I2P Destination Address Required")
        print("="*60)
        print("\nTo find your I2P destination:")
        print("  1. Open i2pd console: http://127.0.0.1:7070")
        print("  2. Go to 'I2P Tunnels' page")
        print("  3. Find 'zerotrace-api' tunnel")
        print("  4. Copy the destination address (ends with .b32.i2p)")
        print("\nOR check the i2pd console window for:")
        print("  'Tunnel created' or 'New destination' messages")
        print("="*60)
        
        while True:
            destination = input("\nEnter your I2P destination address (.b32.i2p): ").strip()
            
            if not destination:
                print("❌ Destination cannot be empty")
                continue
            
            # Validate format (52 character base32 + .b32.i2p)
            if not re.match(r'^[a-z2-7]{52}\.b32\.i2p$', destination):
                print("⚠️  Warning: Address doesn't match expected format")
                confirm = input("Use this address anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue
            
            self.destination = destination
            print(f"✅ I2P destination set: {destination}")
            return destination
    
    def stop(self):
        """Stop i2pd router process."""
        if self.process and self.process.poll() is None:
            print("\n🛑 Stopping i2pd router...")
            self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=5)
                print("✅ i2pd stopped gracefully")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing i2pd...")
                self.process.kill()
                print("✅ i2pd killed")
        else:
            print("⚠️  i2pd is not running")
    
    def is_running(self) -> bool:
        """Check if i2pd process is running.
        
        Returns:
            True if running, False otherwise
        """
        return self.process is not None and self.process.poll() is None
    
    def get_proxy_settings(self) -> Tuple[str, int]:
        """Get HTTP proxy settings for I2P.
        
        Returns:
            (proxy_host, proxy_port) tuple
        """
        # i2pd default HTTP proxy
        return ("127.0.0.1", 4444)
    
    def __del__(self):
        """Cleanup on deletion."""
        # Note: We don't stop i2pd on deletion to allow it to run
        # User should manually stop if desired
        pass


def test_i2p_manager():
    """Test I2P manager functionality."""
    print("Testing I2P Manager...\n")
    
    manager = I2PManager()
    
    # Start i2pd
    if manager.start():
        print("\n" + "="*60)
        
        # Try to get destination
        destination = manager.get_destination()
        
        if not destination:
            # Manual input
            destination = manager.get_destination_manual()
        
        print("\n" + "="*60)
        print("✅ I2P Setup Complete!")
        print(f"   Destination: {destination}")
        print(f"   HTTP Proxy: http://{manager.get_proxy_settings()[0]}:{manager.get_proxy_settings()[1]}")
        print("="*60)
        
        # Keep running
        input("\nPress Enter to stop i2pd...")
        manager.stop()
    else:
        print("\n❌ Failed to start i2pd")


if __name__ == "__main__":
    test_i2p_manager()
