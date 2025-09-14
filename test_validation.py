#!/usr/bin/env python3
"""Test bench validation"""

import sys
from pathlib import Path

# Add the parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from frappebr.core.ssh_manager import SSHManager
from frappebr.core.site_manager import SiteManager

def test_validation():
    print("=== Bench Validation Test ===")
    
    ssh_manager = SSHManager()
    site_manager = SiteManager(ssh_manager)
    
    hostname = "qm.baecktrade.de"
    bench_path = "/home/itsdave/frappe-15"
    
    print(f"Testing validation for: {bench_path}")
    
    required_files = [
        "sites",
        "apps", 
        "config/common_site_config.json"
    ]
    
    for file_path in required_files:
        full_path = f"{bench_path}/{file_path}"
        exists = ssh_manager.file_exists(hostname, full_path)
        print(f"  {full_path}: {'✅' if exists else '❌'}")
        
        if not exists:
            # Try to see what's there
            exit_code, stdout, stderr = ssh_manager.execute_command(
                hostname, f'ls -la "{full_path}" 2>&1'
            )
            print(f"    ls output: {stdout}")
    
    # Test overall validation
    is_valid = site_manager._is_valid_frappe_bench(hostname, bench_path)
    print(f"\nOverall validation: {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    if is_valid:
        print("\n=== Testing Site Listing ===")
        try:
            sites = site_manager.list_sites(hostname, bench_path)
            print(f"Found {len(sites)} sites:")
            for site in sites:
                print(f"  - {site.name}")
        except Exception as e:
            print(f"Site listing failed: {e}")
    
    ssh_manager.disconnect_all()

if __name__ == "__main__":
    test_validation()