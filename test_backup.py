#!/usr/bin/env python3
"""Test backup creation with fixed command"""

import sys
from pathlib import Path

# Add the parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from frappebr.core.ssh_manager import SSHManager
from frappebr.core.backup_manager import BackupManager

def test_backup():
    print("=== Backup Creation Test ===")
    
    ssh_manager = SSHManager()
    backup_manager = BackupManager(ssh_manager)
    
    hostname = "qm.baecktrade.de"
    bench_path = "/home/itsdave/frappe-15"
    site_name = "frappe15.labexposed.com"
    
    print(f"Testing backup creation for: {site_name}")
    
    try:
        # Test the command manually first
        test_command = f'cd "{bench_path}" && bench --site {site_name} --version'
        print(f"\nTesting bench command: {test_command}")
        
        exit_code, stdout, stderr = ssh_manager.execute_command(hostname, test_command)
        print(f"Exit code: {exit_code}")
        print(f"Output: {stdout}")
        if stderr:
            print(f"Error: {stderr}")
        
        if exit_code == 0:
            print("✅ Bench command works! Now testing backup...")
            
            # Test backup creation
            backup_info = backup_manager.create_backup(
                hostname, bench_path, site_name, backup_type="database"
            )
            
            print(f"✅ Backup created successfully!")
            print(f"   Filename: {backup_info.filename}")
            print(f"   Size: {backup_info.size_mb} MB")
            print(f"   Type: {backup_info.backup_type}")
        else:
            print("❌ Bench command failed")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    ssh_manager.disconnect_all()

if __name__ == "__main__":
    test_backup()