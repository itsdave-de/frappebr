#!/usr/bin/env python3
"""Debug SSH connectivity issues."""

import sys
from pathlib import Path

# Add the parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from frappebr.core.ssh_manager import SSHManager, SSHConnectionError
from frappebr.utils.ssh_config import SSHConfigParser

def debug_ssh_connection():
    """Debug SSH connection to qm.baecktrade.de"""
    
    print("=== SSH Connection Debug ===")
    
    # Test SSH config parsing
    print("1. Testing SSH config parsing...")
    parser = SSHConfigParser()
    hosts = parser.parse_config()
    
    target_host = None
    for host in hosts:
        if host.host == "qm.baecktrade.de":
            target_host = host
            break
    
    if not target_host:
        print("❌ Host 'qm.baecktrade.de' not found in SSH config")
        return
    
    print(f"✅ Found host config:")
    print(f"   Host: {target_host.host}")
    print(f"   Hostname: {target_host.hostname}")
    print(f"   User: {target_host.user}")
    print(f"   Port: {target_host.port}")
    print(f"   Identity File: {target_host.identity_file}")
    
    # Test SSH connection with detailed error info
    print("\n2. Testing SSH connection...")
    ssh_manager = SSHManager()
    
    try:
        client = ssh_manager.connect("qm.baecktrade.de", target_host)
        print("✅ SSH connection successful!")
        
        # Test a simple command
        print("\n3. Testing command execution...")
        exit_code, stdout, stderr = ssh_manager.execute_command("qm.baecktrade.de", "whoami")
        print(f"Command: whoami")
        print(f"Exit code: {exit_code}")
        print(f"Output: {stdout}")
        if stderr:
            print(f"Stderr: {stderr}")
        
        ssh_manager.disconnect("qm.baecktrade.de")
        
    except SSHConnectionError as e:
        print(f"❌ SSH connection failed: {e}")
        print("\nDebugging suggestions:")
        print("1. Check if SSH agent is running: ssh-add -l")
        print("2. Test manual connection: ssh qm.baecktrade.de")
        print("3. Check SSH key permissions: ls -la ~/.ssh/")
        
        # Try to get more details
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            print(f"\n4. Raw Paramiko connection test...")
            client.connect(
                hostname=target_host.hostname,
                port=target_host.port,
                username=target_host.user,
                timeout=10,
                allow_agent=True,
                look_for_keys=True
            )
            print("✅ Raw Paramiko connection successful!")
            client.close()
            
        except Exception as e2:
            print(f"❌ Raw Paramiko connection also failed: {e2}")
            print(f"Exception type: {type(e2).__name__}")

if __name__ == "__main__":
    debug_ssh_connection()