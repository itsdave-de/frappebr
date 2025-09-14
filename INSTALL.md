# Installation Guide for FrappeBR

This guide provides detailed installation instructions for FrappeBR on different platforms.

## 📋 Prerequisites

Before installing FrappeBR, ensure you have the following prerequisites:

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows (with WSL recommended)
- **Memory**: At least 512MB RAM available
- **Disk Space**: 100MB for installation, additional space for backups

### Required Access
- **SSH Access**: SSH key-based authentication to target Frappe servers
- **Network**: Internet access for package downloads
- **Permissions**: Ability to install Python packages (or virtual environment access)

### Dependencies
The following will be installed automatically:
- `paramiko>=3.3.1` - SSH client library
- `rich>=13.6.0` - Terminal formatting and UI
- `pydantic>=2.4.0` - Data validation
- `cryptography>=41.0.0` - Cryptographic functions
- Additional dependencies (see `requirements.txt`)

## 🚀 Installation Methods

### Method 1: Development Installation (Recommended for Developers)

This method installs FrappeBR in development mode, allowing you to modify the code and see changes immediately.

```bash
# 1. Clone the repository
git clone <repository-url>
cd frappebr

# 2. Create a virtual environment (recommended)
python -m venv frappebr-env
source frappebr-env/bin/activate  # On Windows: frappebr-env\Scripts\activate

# 3. Install in development mode
pip install -e .

# 4. (Optional) Install with development dependencies
pip install -e .[dev]

# 5. Verify installation
frappebr --help
```

### Method 2: User Installation

This method installs FrappeBR as a regular package for end users.

```bash
# 1. Create a virtual environment (recommended)
python -m venv frappebr-env
source frappebr-env/bin/activate  # On Windows: frappebr-env\Scripts\activate

# 2. Install from source
pip install git+<repository-url>

# 3. Verify installation
frappebr --help
```

### Method 3: Local Installation

If you have the source code locally but don't need development features.

```bash
# 1. Navigate to the project directory
cd /path/to/frappebr

# 2. Create and activate virtual environment
python -m venv frappebr-env
source frappebr-env/bin/activate  # On Windows: frappebr-env\Scripts\activate

# 3. Install
pip install .

# 4. Verify installation
frappebr --help
```

## 🔧 Post-Installation Setup

### 1. SSH Configuration

FrappeBR uses your SSH configuration from `~/.ssh/config`. Set up your Frappe servers:

```bash
# Edit SSH config
nano ~/.ssh/config
```

Add your servers:
```ssh-config
Host production-frappe
    HostName your-production-server.com
    User frappe
    IdentityFile ~/.ssh/id_rsa
    Port 22

Host staging-frappe
    HostName staging.your-domain.com
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519
    Port 2222
```

### 2. SSH Key Setup

Ensure your SSH keys are properly set up:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# Add key to SSH agent
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_rsa

# Copy public key to servers
ssh-copy-id -i ~/.ssh/id_rsa.pub user@your-server.com
```

### 3. Test SSH Connection

Verify you can connect to your Frappe servers:

```bash
# Test connection
ssh production-frappe

# Test with FrappeBR (should show connection test)
python -c "from frappebr.core.ssh_manager import SSHManager; ssh = SSHManager(); print('SSH manager loaded successfully')"
```

### 4. Create Backup Directory

FrappeBR stores backups locally by default:

```bash
# Default backup directory
mkdir -p ~/frappebr-backups

# Or specify custom directory (will be configurable in future versions)
mkdir -p /path/to/your/backups
```

## 🧪 Verify Installation

### Quick Test

```bash
# Run FrappeBR
frappebr

# You should see the main menu
```

### Comprehensive Test

```bash
# Test SSH connections
python -c "
from frappebr.core.ssh_manager import SSHManager
ssh = SSHManager()
hosts = ssh.list_hosts()
print(f'Found {len(hosts)} SSH hosts configured')
for host in hosts:
    print(f'  - {host.hostname} ({host.user}@{host.host})')
"

# Test Rich UI components
python -c "
from frappebr.ui.console import ConsoleUI
ui = ConsoleUI()
ui.print_success('Installation test successful!')
"
```

## 🐧 Platform-Specific Instructions

### Ubuntu/Debian

```bash
# Install system dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# Install FrappeBR
python3 -m venv frappebr-env
source frappebr-env/bin/activate
pip install git+<repository-url>
```

### CentOS/RHEL

```bash
# Install system dependencies
sudo yum update
sudo yum install python3 python3-pip git

# Install FrappeBR
python3 -m venv frappebr-env
source frappebr-env/bin/activate
pip install git+<repository-url>
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and Git
brew install python git

# Install FrappeBR
python3 -m venv frappebr-env
source frappebr-env/bin/activate
pip install git+<repository-url>
```

### Windows (with WSL)

```bash
# Install WSL and Ubuntu
wsl --install Ubuntu

# In WSL terminal:
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# Install FrappeBR
python3 -m venv frappebr-env
source frappebr-env/bin/activate
pip install git+<repository-url>
```

## 🔧 Development Setup

For contributors and developers who want to modify FrappeBR:

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-username/frappebr.git
cd frappebr

# 2. Create development environment
python -m venv dev-env
source dev-env/bin/activate

# 3. Install with development dependencies
pip install -e .[dev]

# 4. Install pre-commit hooks (if available)
pre-commit install

# 5. Run tests to verify setup
pytest tests/

# 6. Run code formatting
black .
isort .

# 7. Run type checking
mypy .
```

## 🚫 Troubleshooting Installation

### Common Issues

#### Python Version Issues
```
ERROR: This package requires Python 3.8 or higher
```
**Solution**: Install Python 3.8+ or use pyenv to manage Python versions.

#### Permission Errors
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```
**Solution**: Use virtual environments or add `--user` flag to pip install.

#### SSH Key Issues
```
Authentication failed (publickey)
```
**Solution**: 
- Ensure SSH keys are generated: `ssh-keygen -t rsa`
- Add keys to SSH agent: `ssh-add ~/.ssh/id_rsa`
- Copy keys to servers: `ssh-copy-id user@server`

#### Missing System Dependencies
```
error: Microsoft Visual C++ 14.0 is required
```
**Solution** (Windows): Install Microsoft C++ Build Tools or Visual Studio.

#### Network/Firewall Issues
```
Could not fetch URL https://pypi.org/simple/
```
**Solution**: Check internet connection, proxy settings, or use `--trusted-host pypi.org`

### Getting Help

If you encounter issues:

1. **Check this guide**: Look for your specific error above
2. **Check logs**: Run with `--debug` flag for detailed output
3. **GitHub Issues**: Search existing issues or create a new one
4. **System Info**: Include Python version, OS, and error messages

## 🔄 Updating FrappeBR

### Development Installation
```bash
# Navigate to project directory
cd frappebr

# Pull latest changes
git pull origin main

# Update dependencies
pip install -e .[dev]
```

### User Installation
```bash
# Reinstall from latest source
pip install --upgrade git+<repository-url>
```

## 🗑️ Uninstalling

### Remove FrappeBR
```bash
# Uninstall package
pip uninstall frappebr

# Remove virtual environment
deactivate
rm -rf frappebr-env

# Remove backup directories (optional)
rm -rf ~/frappebr-backups
```

### Clean System
```bash
# Remove SSH config entries (manually edit ~/.ssh/config)
# Remove any custom backup directories
# Remove any log files or temporary data
```

---

**Need Help?** Create an issue on GitHub or check the main README.md for additional troubleshooting information.