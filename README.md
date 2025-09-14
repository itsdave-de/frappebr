# FrappeBR - Frappe Backup & Restore Tool

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Python CLI tool with a rich console interface for managing Frappe site backups and restores across multiple environments. FrappeBR simplifies the complex process of backing up, transferring, and restoring Frappe sites with an intuitive menu-driven interface.

## ✨ Features

### 🔐 Secure SSH Operations
- **SSH Key Authentication**: Connect to remote hosts using SSH key authentication with passphrase support
- **SSH Agent Integration**: Seamless integration with SSH agent for secure key management
- **Multi-Host Support**: Manage multiple remote servers from SSH config

### 🏗️ Intelligent Site Discovery
- **Automatic Detection**: Automatically discover Frappe bench directories on remote systems
- **Site Validation**: Validate Frappe site structure and configuration
- **Multi-Bench Support**: Handle multiple frappe-bench installations per server

### 💾 Advanced Backup Management
- **Multiple Backup Types**: Support for database-only, files-only, and complete backups
- **Backup Sets**: Group related backup files (database + config + public files + private files)
- **Progress Tracking**: Real-time progress bars with transfer speeds and ETA
- **Compression Support**: Handle compressed backup files (.gz, .tar)

### 📁 Smart File Transfer
- **Secure Transfer**: SFTP-based file transfers with integrity verification
- **Resume Support**: Resume interrupted downloads automatically
- **Batch Operations**: Download complete backup sets in one operation
- **Local Storage**: Organized local backup storage with automatic grouping

### 🔧 Comprehensive Restore
- **Site-Based Restore**: Create new sites or restore to existing ones
- **Multi-File Support**: Handle complete backup sets with all components
- **Database Management**: Let Frappe manage database naming automatically
- **Force Restore**: Override existing sites when needed
- **Post-Restore Tasks**: Automatic migration, cache clearing, and website rebuild

### 🎨 Rich Console Interface
- **Interactive Menus**: Intuitive menu-driven interface with Rich console UI
- **Progress Visualization**: Beautiful progress bars and status indicators
- **Error Handling**: Clear error messages and graceful failure handling
- **Confirmation Prompts**: Safety confirmations for destructive operations

## 📋 Requirements

- **Python**: 3.8 or higher
- **SSH Access**: SSH key-based authentication to Frappe servers
- **Frappe Framework**: Installed on target systems
- **MariaDB/MySQL**: Database server with appropriate permissions for restore operations

## 🚀 Installation

### Option 1: Development Installation (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd frappebr

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e .[dev]
```

### Option 2: Direct Installation

```bash
# Install directly from source
pip install git+<repository-url>
```

### Option 3: Local Installation

```bash
# If you have the source code locally
pip install .
```

## 🔧 Configuration

### SSH Configuration

FrappeBR reads your SSH configuration from `~/.ssh/config`. Set up your hosts:

```ssh-config
Host production-server
    HostName your-server.com
    User itsdave
    IdentityFile ~/.ssh/id_rsa
    Port 22

Host staging-server
    HostName staging.your-server.com
    User frappe
    IdentityFile ~/.ssh/id_ed25519
    Port 2222
```

### SSH Agent Setup

For passphrase-protected keys, use SSH agent:

```bash
# Start SSH agent
eval $(ssh-agent)

# Add your SSH key
ssh-add ~/.ssh/id_rsa

# Verify keys are loaded
ssh-add -l
```

## 💻 Usage

### Basic Usage

Simply run the command to start the interactive interface:

```bash
frappebr
```

### Main Menu Options

1. **Connect to Remote Host** - Connect to a Frappe server and manage backups
2. **Manage Local Backups** - View and manage locally stored backup sets
3. **Restore from Backup** - Restore sites from local backup sets
4. **Settings & Configuration** - Configure application settings (coming soon)
5. **View Operation History** - View backup/restore operation history (coming soon)
6. **Exit** - Exit the application

### Typical Workflow

#### Creating and Downloading Backups

1. **Select "Connect to Remote Host"**
2. **Choose SSH Host** from your configured hosts or enter manually
3. **Select Frappe Bench** from discovered bench directories
4. **Choose Site** from available Frappe sites
5. **Create Backup**:
   - Choose backup type (Complete/Database/Files)
   - Monitor creation progress
   - Optionally download immediately
6. **Download Existing Backups**:
   - Browse available backup sets
   - Download complete backup sets with progress tracking

#### Restoring Backups

1. **Select "Restore from Backup"**
2. **Choose Backup Set** from locally available backups
3. **Configure Restore**:
   - Set target bench path
   - Choose to create new site or restore to existing
   - Enter MariaDB credentials
4. **Confirm and Execute**:
   - Review restore configuration
   - Execute restore with progress monitoring
   - Run post-restore tasks (migrate, rebuild)

### Command Examples

The tool uses the following Frappe bench commands internally:

```bash
# Create complete backup
bench --site mysite.com backup --with-files

# Create database-only backup
bench --site mysite.com backup --only-db

# Restore from backup set
bench --site newsite.com restore database.sql.gz \
  --with-public-files public.tar \
  --with-private-files private.tar \
  --mariadb-root-username root \
  --mariadb-root-password password \
  --force
```

## 📊 Backup Set Structure

FrappeBR organizes backups into logical sets based on timestamp:

```
backups/
├── 20250909_143022-mysite_com-database.sql.gz
├── 20250909_143022-mysite_com-config.json
├── 20250909_143022-mysite_com-public.tar
└── 20250909_143022-mysite_com-private.tar
```

Each backup set contains:
- **Database backup**: Site database dump (`.sql.gz`)
- **Configuration**: Site configuration files (`.json`)
- **Public files**: Public file archives (`.tar`)
- **Private files**: Private file archives (`.tar`)

## 🔍 Troubleshooting

### Common Issues

#### SSH Connection Failures
```
Error: SSH connection failed: Authentication failed
```
**Solution**: 
- Ensure SSH keys are added to SSH agent: `ssh-add ~/.ssh/id_rsa`
- Verify SSH configuration: `ssh -T hostname`
- Check SSH agent is running: `ssh-add -l`

#### Site Discovery Problems
```
Warning: No frappe-bench directories found
```
**Solution**:
- Verify Frappe is installed at expected paths
- Check directory permissions
- Ensure `sites/common_site_config.json` exists

#### Bench Command Not Found
```
Error: bash: bench: command not found
```
**Solution**:
- Verify bench is in PATH on remote system
- Check bench installation: `which bench`
- Update backup manager if bench is in custom location

#### Database Restore Failures
```
Error: Restore failed: Access denied for user 'root'
```
**Solution**:
- Verify MariaDB credentials
- Ensure database user has CREATE and DROP privileges
- Check MariaDB service is running

### Debug Mode

Run with debug flag for detailed logging:

```bash
python -m frappebr --debug
```

## 🏗️ Architecture

### Core Components

- **CLI Interface** (`cli.py`): Main application orchestrator
- **SSH Manager** (`core/ssh_manager.py`): Secure SSH connection management
- **Site Manager** (`core/site_manager.py`): Frappe site discovery and validation
- **Backup Manager** (`core/backup_manager.py`): Backup creation and listing
- **Transfer Manager** (`core/transfer_manager.py`): Secure file transfer with progress
- **Restore Manager** (`core/restore_manager.py`): Site restoration operations
- **Console UI** (`ui/console.py`): Rich terminal interface

### Data Models

- **BackupInfo**: Individual backup file metadata
- **BackupSet**: Grouped backup files by timestamp
- **RestoreConfig**: Restoration operation configuration
- **SSHConfig**: SSH connection parameters
- **SiteInfo**: Frappe site information

## 🤝 Contributing

### Development Setup

```bash
# Clone and install with development dependencies
git clone <repository-url>
cd frappebr
pip install -e .[dev]

# Run tests
pytest tests/

# Format code
black .
isort .

# Type checking
mypy .
```

### Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting
- Add type hints for all functions
- Write docstrings for public methods
- Include tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Frappe Framework** - The powerful framework this tool supports
- **Rich Library** - Beautiful terminal interface components
- **Paramiko** - Secure SSH client implementation
- **Pydantic** - Data validation and settings management

---
