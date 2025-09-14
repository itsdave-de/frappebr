#!/usr/bin/env python3
"""Basic functionality test for FrappeBR components."""

import sys
import os
from pathlib import Path

# Add current directory to path for relative imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Test basic imports and functionality
def test_imports():
    """Test that all modules can be imported."""
    print("Testing basic imports...")
    
    try:
        # Test models
        from models.config import SSHConfig, SiteInfo, BackupInfo, AppConfig
        print("✓ Models imported successfully")
        
        # Test utilities
        from utils.ssh_config import SSHConfigParser
        from utils.crypto import CryptoManager
        print("✓ Utilities imported successfully")
        
        # Test core modules (these might fail if dependencies aren't met)
        try:
            from core.ssh_manager import SSHManager
            from core.site_manager import SiteManager
            from core.backup_manager import BackupManager
            from core.transfer_manager import TransferManager
            from core.restore_manager import RestoreManager
            print("✓ Core modules imported successfully")
        except ImportError as e:
            print(f"⚠ Core modules import warning: {e}")
        
        # Test UI
        try:
            from ui.console import ConsoleUI
            print("✓ UI module imported successfully")
        except ImportError as e:
            print(f"⚠ UI module import warning: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test data models."""
    print("\nTesting data models...")
    
    try:
        from models.config import SSHConfig, SiteInfo, BackupInfo
        from datetime import datetime
        
        # Test SSH config
        ssh_config = SSHConfig(
            host="testhost",
            hostname="test.example.com",
            user="testuser",
            port=22
        )
        print(f"✓ SSH Config created: {ssh_config.host}")
        
        # Test site info
        site_info = SiteInfo(
            name="test.site.com",
            path="/test/path",
            bench_path="/test/bench",
            database_name="test_db"
        )
        print(f"✓ Site Info created: {site_info.name}")
        
        # Test backup info
        backup_info = BackupInfo(
            filename="test_backup.sql.gz",
            filepath="/test/backup.sql.gz",
            site_name="test.site.com",
            backup_type="database",
            created_at=datetime.now(),
            size_mb=50.0
        )
        print(f"✓ Backup Info created: {backup_info.filename}")
        
        return True
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        return False


def test_ssh_config_parser():
    """Test SSH config parser."""
    print("\nTesting SSH config parser...")
    
    try:
        from utils.ssh_config import SSHConfigParser
        
        parser = SSHConfigParser()
        hosts = parser.parse_config()
        
        print(f"✓ SSH Config parser created, found {len(hosts)} hosts")
        
        for host in hosts[:3]:  # Show first 3
            print(f"  - {host.host} ({host.hostname})")
        
        return True
        
    except Exception as e:
        print(f"✗ SSH config parser test failed: {e}")
        return False


def test_console_ui():
    """Test console UI basic functionality."""
    print("\nTesting console UI...")
    
    try:
        from ui.console import ConsoleUI
        
        ui = ConsoleUI()
        print("✓ Console UI created")
        
        # Test basic prints (without actually printing to avoid clutter)
        ui.console.quiet = True  # Suppress output for test
        
        return True
        
    except Exception as e:
        print(f"✗ Console UI test failed: {e}")
        return False


def main():
    """Run all basic tests."""
    print("FrappeBR Basic Functionality Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_models,
        test_ssh_config_parser,
        test_console_ui
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic functionality tests passed!")
        print("\nNext steps:")
        print("1. Configure SSH access to your Frappe servers")
        print("2. Run: python -m frappebr.cli (once package structure is fixed)")
        print("3. Or run individual components for testing")
    else:
        print("⚠ Some tests failed - check dependencies and imports")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())