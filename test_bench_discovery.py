#!/usr/bin/env python3
"""Test bench discovery on qm.baecktrade.de"""

import sys
from pathlib import Path

# Add the parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from frappebr.core.ssh_manager import SSHManager
from frappebr.core.site_manager import SiteManager

def test_bench_discovery():
    print("=== Frappe Bench Discovery Test ===")
    
    ssh_manager = SSHManager()
    site_manager = SiteManager(ssh_manager)
    
    hostname = "qm.baecktrade.de"
    
    print(f"1. Searching for frappe benches on {hostname}...")
    
    # Test with manual paths first
    manual_paths = [
        "/home/itsdave/frappe-15",
        "/home/*/frappe-*",
        "/home/itsdave/frappe-*"
    ]
    
    benches = site_manager.find_frappe_benches(hostname, manual_paths)
    print(f"Found {len(benches)} benches: {benches}")
    
    if not benches:
        print("\n2. Let's try some direct commands to debug...")
        
        # Test direct commands
        commands = [
            "ls -la /home/itsdave/",
            "ls -la /home/itsdave/frappe-15/",
            "ls -la /home/itsdave/frappe-15/sites/",
            "find /home/itsdave -name 'frappe-*' -type d -maxdepth 1"
        ]
        
        for cmd in commands:
            try:
                print(f"\nTesting: {cmd}")
                exit_code, stdout, stderr = ssh_manager.execute_command(hostname, cmd)
                print(f"Exit code: {exit_code}")
                if stdout:
                    print(f"Output:\n{stdout}")
                if stderr:
                    print(f"Error:\n{stderr}")
            except Exception as e:
                print(f"Command failed: {e}")
    
    else:
        print(f"\n2. Testing site discovery in first bench: {benches[0]}")
        try:
            sites = site_manager.list_sites(hostname, benches[0])
            print(f"Found {len(sites)} sites:")
            for site in sites:
                print(f"  - {site.name} ({site.size_mb}MB)")
        except Exception as e:
            print(f"Site listing failed: {e}")
    
    ssh_manager.disconnect_all()

if __name__ == "__main__":
    test_bench_discovery()