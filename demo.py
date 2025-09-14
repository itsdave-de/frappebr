#!/usr/bin/env python3
"""Demo script to test FrappeBR functionality."""

import sys
from pathlib import Path

# Add the current directory to the path so we can import frappebr
sys.path.insert(0, str(Path(__file__).parent))

from frappebr.core.ssh_manager import SSHManager
from frappebr.core.site_manager import SiteManager
from frappebr.ui.console import ConsoleUI


def demo_ssh_config_parsing():
    """Demo SSH config parsing."""
    print("=== SSH Config Parsing Demo ===")
    
    ssh_manager = SSHManager()
    hosts = ssh_manager.list_hosts()
    
    if hosts:
        print(f"Found {len(hosts)} SSH hosts in config:")
        for i, host in enumerate(hosts, 1):
            print(f"  {i}. {host.host} ({host.hostname}) - {host.user}")
    else:
        print("No SSH hosts found in ~/.ssh/config")
    
    print()


def demo_console_interface():
    """Demo console interface."""
    print("=== Console Interface Demo ===")
    
    ui = ConsoleUI()
    ui.print_header()
    ui.print_success("This is a success message")
    ui.print_warning("This is a warning message") 
    ui.print_error("This is an error message")
    ui.print_info("This is an info message")
    
    print()


def demo_site_manager():
    """Demo site manager functionality."""
    print("=== Site Manager Demo ===")
    
    ssh_manager = SSHManager()
    site_manager = SiteManager(ssh_manager)
    
    # Demo with localhost (will fail but shows the workflow)
    try:
        print("Testing site discovery on localhost...")
        benches = site_manager.find_frappe_benches("localhost", ["/tmp/test-bench"])
        print(f"Found {len(benches)} benches")
    except Exception as e:
        print(f"Site discovery failed (expected): {e}")
    
    print()


def demo_models():
    """Demo data models."""
    print("=== Data Models Demo ===")
    
    from frappebr.models.config import SSHConfig, SiteInfo, BackupInfo
    from datetime import datetime
    
    # Create sample SSH config
    ssh_config = SSHConfig(
        host="myserver",
        hostname="myserver.example.com", 
        user="frappe",
        port=22
    )
    print(f"SSH Config: {ssh_config.host} -> {ssh_config.hostname}")
    
    # Create sample site info
    site_info = SiteInfo(
        name="mysite.example.com",
        path="/home/frappe/frappe-bench/sites/mysite.example.com",
        bench_path="/home/frappe/frappe-bench",
        is_active=True,
        apps=["frappe", "erpnext"],
        database_name="mysite_db",
        size_mb=150.5
    )
    print(f"Site: {site_info.name} ({site_info.size_mb}MB)")
    
    # Create sample backup info
    backup_info = BackupInfo(
        filename="mysite_20231201_143022_database.sql.gz",
        filepath="/home/frappe/frappe-bench/sites/mysite.example.com/private/backups/mysite_20231201_143022_database.sql.gz",
        site_name="mysite.example.com",
        backup_type="database",
        created_at=datetime.now(),
        size_mb=45.2,
        compressed=True
    )
    print(f"Backup: {backup_info.filename} ({backup_info.size_mb}MB)")
    
    print()


def main():
    """Run all demos."""
    print("FrappeBR Functionality Demo")
    print("="*50)
    
    try:
        demo_models()
        demo_console_interface()
        demo_ssh_config_parsing()
        demo_site_manager()
        
        print("=== Demo Complete ===")
        print("All components loaded successfully!")
        print("Ready to run: python -m frappebr.cli")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())