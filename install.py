#!/usr/bin/env python3
"""Installation and setup script for FrappeBR."""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)


def create_directories():
    """Create necessary directories."""
    dirs = [
        Path.home() / ".frappebr",
        Path.home() / ".frappebr" / "backups",
        Path.home() / ".frappebr" / "logs",
    ]
    
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def create_config_file():
    """Create default configuration file."""
    config_file = Path.home() / ".frappebr" / "config.json"
    
    if not config_file.exists():
        default_config = {
            "backup_storage_path": str(Path.home() / ".frappebr" / "backups"),
            "log_level": "INFO",
            "ssh_timeout": 30,
            "transfer_timeout": 3600,
            "max_concurrent_transfers": 3,
            "compression_level": 6,
            "backup_retention_days": 30,
            "auto_cleanup": False
        }
        
        import json
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"✓ Created config file: {config_file}")
    else:
        print(f"✓ Config file already exists: {config_file}")


def install_package():
    """Install the package in development mode."""
    print("Installing FrappeBR package...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], check=True)
        print("✓ Package installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing package: {e}")
        sys.exit(1)


def test_installation():
    """Test if installation was successful."""
    print("Testing installation...")
    
    try:
        import frappebr
        print(f"✓ FrappeBR {frappebr.__version__} imported successfully")
        
        # Test CLI command
        result = subprocess.run([
            sys.executable, "-c", "from frappebr.cli import main; print('CLI import successful')"
        ], capture_output=True, text=True, check=True)
        
        print("✓ CLI functionality verified")
    except Exception as e:
        print(f"Error testing installation: {e}")
        sys.exit(1)


def print_usage_info():
    """Print usage information."""
    print("\n" + "="*60)
    print("Installation completed successfully!")
    print("="*60)
    print("\nUsage:")
    print("  frappebr                 # Start the interactive interface")
    print("  python -m frappebr.cli   # Alternative way to run")
    print("\nConfiguration:")
    print(f"  Config file: {Path.home() / '.frappebr' / 'config.json'}")
    print(f"  Backups dir: {Path.home() / '.frappebr' / 'backups'}")
    print(f"  Logs dir:    {Path.home() / '.frappebr' / 'logs'}")
    print("\nBefore using:")
    print("1. Ensure you have SSH access to your Frappe servers")
    print("2. Configure your ~/.ssh/config with host definitions")
    print("3. Test SSH key authentication to your servers")
    print("\nFor help: frappebr --help")
    print("="*60)


def main():
    """Main installation function."""
    print("FrappeBR Installation Script")
    print("="*40)
    
    check_python_version()
    install_dependencies()
    create_directories()
    create_config_file()
    install_package()
    test_installation()
    print_usage_info()


if __name__ == "__main__":
    main()