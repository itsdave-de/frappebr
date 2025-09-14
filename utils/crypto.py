"""Cryptographic utilities for FrappeBR."""

import json
import base64
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from pathlib import Path


class CryptoManager:
    """Handle encryption key management and operations."""
    
    def __init__(self):
        self.key = None
    
    def generate_key(self) -> str:
        """Generate a new encryption key."""
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()
    
    def extract_encryption_key_from_config(self, site_config: Dict[str, Any]) -> Optional[str]:
        """Extract encryption key from site configuration."""
        return site_config.get('encryption_key')
    
    def extract_encryption_key_from_backup(self, backup_path: str, 
                                          site_name: str) -> Optional[str]:
        """Extract encryption key from backup file."""
        # This is a simplified implementation
        # In practice, you'd need to extract the site_config.json from the backup
        
        backup_file = Path(backup_path)
        
        if backup_file.suffix == '.gz':
            # For database backups, the encryption key might be in comments
            # or we need to extract it from an associated config backup
            return None
        
        elif backup_file.suffix in ['.tar', '.tgz']:
            # For file backups, extract site_config.json
            return self._extract_key_from_tar(backup_path, site_name)
        
        return None
    
    def _extract_key_from_tar(self, backup_path: str, site_name: str) -> Optional[str]:
        """Extract encryption key from tar backup."""
        import tarfile
        
        try:
            with tarfile.open(backup_path, 'r:*') as tar:
                # Look for site_config.json in the archive
                config_path = f"{site_name}/site_config.json"
                
                try:
                    config_file = tar.extractfile(config_path)
                    if config_file:
                        config_data = json.loads(config_file.read().decode())
                        return config_data.get('encryption_key')
                except KeyError:
                    pass
                
                # Alternative paths
                for member in tar.getmembers():
                    if member.name.endswith('site_config.json'):
                        config_file = tar.extractfile(member)
                        if config_file:
                            try:
                                config_data = json.loads(config_file.read().decode())
                                if 'encryption_key' in config_data:
                                    return config_data['encryption_key']
                            except:
                                continue
        
        except Exception as e:
            print(f"Error extracting encryption key from {backup_path}: {e}")
        
        return None
    
    def update_site_config_with_key(self, site_config_path: str, 
                                   encryption_key: str) -> bool:
        """Update site configuration with encryption key."""
        try:
            config_file = Path(site_config_path)
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            config['encryption_key'] = encryption_key
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
        
        except Exception as e:
            print(f"Error updating site config with encryption key: {e}")
            return False
    
    def backup_encryption_key(self, site_config: Dict[str, Any], 
                             backup_dir: str, site_name: str) -> Optional[str]:
        """Backup encryption key to separate file."""
        encryption_key = site_config.get('encryption_key')
        if not encryption_key:
            return None
        
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            key_file = backup_path / f"{site_name}_encryption_key.json"
            
            key_data = {
                'site_name': site_name,
                'encryption_key': encryption_key,
                'backup_timestamp': str(Path().cwd())  # Placeholder
            }
            
            with open(key_file, 'w') as f:
                json.dump(key_data, f, indent=2)
            
            return str(key_file)
        
        except Exception as e:
            print(f"Error backing up encryption key: {e}")
            return None
    
    def restore_encryption_key(self, key_backup_file: str) -> Optional[str]:
        """Restore encryption key from backup file."""
        try:
            with open(key_backup_file, 'r') as f:
                key_data = json.load(f)
            
            return key_data.get('encryption_key')
        
        except Exception as e:
            print(f"Error restoring encryption key: {e}")
            return None
    
    def validate_encryption_key(self, encryption_key: str) -> bool:
        """Validate that an encryption key is properly formatted."""
        try:
            # Basic validation - should be base64 encoded
            decoded = base64.urlsafe_b64decode(encryption_key.encode())
            return len(decoded) >= 32  # Minimum key length
        except:
            return False