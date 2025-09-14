"""Frappe site restore functionality."""

import os
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .ssh_manager import SSHManager, SSHConnectionError
from ..models.config import BackupInfo, BackupSet, RestoreConfig
from ..utils.crypto import CryptoManager


class RestoreError(Exception):
    """Restore operation related errors."""
    pass


class RestoreManager:
    """Manages Frappe site restoration operations."""
    
    def __init__(self, ssh_manager: Optional[SSHManager] = None):
        self.ssh_manager = ssh_manager
        self.crypto_manager = CryptoManager()
    
    def restore_site(self, restore_config: RestoreConfig, 
                    local_restore: bool = True) -> bool:
        """Restore a site from backup set."""
        backup_set = restore_config.backup_set
        
        # Validate backup files exist
        for backup_file in backup_set.files:
            backup_path = Path(backup_file.filepath)
            if not backup_path.exists():
                raise RestoreError(f"Backup file not found: {backup_file.filepath}")
        
        if local_restore:
            return self._restore_local_site(restore_config)
        else:
            if not self.ssh_manager:
                raise RestoreError("SSH manager required for remote restore")
            return self._restore_remote_site(restore_config)
    
    def _restore_local_site(self, restore_config: RestoreConfig) -> bool:
        """Restore site to local frappe-bench using proper bench restore command."""
        try:
            bench_path = Path(restore_config.target_bench_path).expanduser().resolve()
            
            if not self._validate_local_bench(bench_path):
                raise RestoreError(f"Invalid frappe-bench directory: {bench_path}")
            
            backup_set = restore_config.backup_set
            
            # Find the database backup file
            database_backup = None
            public_files_backup = None
            private_files_backup = None
            
            for backup_file in backup_set.files:
                if 'database' in backup_file.filename or backup_file.filename.endswith('.sql.gz'):
                    database_backup = backup_file
                elif 'public' in backup_file.filename.lower():
                    public_files_backup = backup_file
                elif 'private' in backup_file.filename.lower():
                    private_files_backup = backup_file
            
            if not database_backup:
                raise RestoreError("No database backup found in backup set")
            
            # Create new site if needed
            if restore_config.create_new_site:
                success = self._create_new_site(bench_path, restore_config.target_site_name)
                if not success:
                    return False
            
            # Use bench restore command
            return self._execute_bench_restore(
                bench_path, 
                restore_config, 
                database_backup.filepath,
                public_files_backup.filepath if public_files_backup else None,
                private_files_backup.filepath if private_files_backup else None
            )
            
        except Exception as e:
            raise RestoreError(f"Local restore failed: {e}")
    
    def _restore_remote_site(self, restore_config: RestoreConfig) -> bool:
        """Restore site to remote frappe-bench (not implemented in this version)."""
        raise NotImplementedError("Remote restore not implemented yet")
    
    def _validate_local_bench(self, bench_path: Path) -> bool:
        """Validate local frappe-bench directory."""
        required_paths = [
            bench_path / "sites",
            bench_path / "apps",
            bench_path / "sites" / "common_site_config.json"
        ]
        
        return all(path.exists() for path in required_paths)
    
    def _execute_bench_restore(self, bench_path: Path, restore_config: RestoreConfig,
                              database_file: str, public_files: str = None, 
                              private_files: str = None) -> bool:
        """Execute bench restore command with proper parameters."""
        try:
            os.chdir(bench_path)
            
            # Build the bench restore command
            cmd = [
                "bench", "--site", restore_config.target_site_name,
                "restore", database_file
            ]
            
            # Add file restoration options
            if public_files and Path(public_files).exists():
                cmd.extend(["--with-public-files", public_files])
            
            if private_files and Path(private_files).exists():
                cmd.extend(["--with-private-files", private_files])
            
            # Add MariaDB credentials
            if restore_config.mariadb_root_username:
                cmd.extend(["--mariadb-root-username", restore_config.mariadb_root_username])
            
            if restore_config.mariadb_root_password:
                cmd.extend(["--mariadb-root-password", restore_config.mariadb_root_password])
            
            # Add force flag
            if restore_config.force_restore:
                cmd.append("--force")
            
            print(f"Executing restore command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Restore failed: {result.stderr}")
                print(f"Stdout: {result.stdout}")
                return False
            
            print("Restore completed successfully")
            print(f"Output: {result.stdout}")
            return True
            
        except Exception as e:
            print(f"Error executing restore: {e}")
            return False
    
    
    
    def _create_new_site(self, bench_path: Path, site_name: str) -> bool:
        """Create a new Frappe site."""
        try:
            os.chdir(bench_path)
            
            # Create new site command (let Frappe manage the database name)
            cmd = [
                "bench", "new-site", site_name,
                "--admin-password", "admin"  # Default password, can be changed later
            ]
            
            print(f"Creating new site: {site_name}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Site creation failed: {result.stderr}")
                return False
            
            print(f"Site created successfully: {site_name}")
            return True
            
        except Exception as e:
            print(f"Error creating site: {e}")
            return False
    
    
    
    
    
    def validate_restore_config(self, restore_config: RestoreConfig) -> Tuple[bool, str]:
        """Validate restore configuration."""
        # Check target bench path
        bench_path = Path(restore_config.target_bench_path).expanduser()
        if not bench_path.exists():
            return False, f"Target bench path does not exist: {bench_path}"
        
        if not self._validate_local_bench(bench_path):
            return False, f"Invalid frappe-bench directory: {bench_path}"
        
        # Check if site already exists when not creating new
        if not restore_config.create_new_site:
            target_site_path = bench_path / "sites" / restore_config.target_site_name
            if not target_site_path.exists():
                return False, f"Target site does not exist: {restore_config.target_site_name}"
        
        # Validate backup set has required files
        backup_set = restore_config.backup_set
        has_database = any('database' in f.filename or f.filename.endswith('.sql.gz') for f in backup_set.files)
        if not has_database:
            return False, "Backup set must contain a database backup file"
        
        return True, "Configuration valid"
    
    def get_site_config(self, bench_path: str, site_name: str) -> Dict[str, Any]:
        """Get site configuration from a local site."""
        config_path = Path(bench_path) / "sites" / site_name / "site_config.json"
        
        if not config_path.exists():
            raise RestoreError(f"Site config not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise RestoreError(f"Failed to read site config: {e}")
    
    def update_site_config(self, bench_path: str, site_name: str, config_updates: Dict[str, Any]):
        """Update site configuration."""
        config_path = Path(bench_path) / "sites" / site_name / "site_config.json"
        
        try:
            # Read existing config
            if config_path.exists():
                with open(config_path, 'r') as f:
                    site_config = json.load(f)
            else:
                site_config = {}
            
            # Apply updates
            site_config.update(config_updates)
            
            # Write updated config
            with open(config_path, 'w') as f:
                json.dump(site_config, f, indent=2)
            
            print(f"Site config updated for {site_name}")
            
        except Exception as e:
            raise RestoreError(f"Failed to update site config: {e}")
    
    def post_restore_tasks(self, restore_config: RestoreConfig, bench_path: Path):
        """Run post-restore tasks like migrate, rebuild, etc."""
        try:
            os.chdir(bench_path)
            
            # Migrate the site
            print("Running database migration...")
            migrate_cmd = ["bench", "--site", restore_config.target_site_name, "migrate"]
            result = subprocess.run(migrate_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Warning: Migration failed: {result.stderr}")
            
            # Clear cache
            print("Clearing cache...")
            clear_cache_cmd = ["bench", "--site", restore_config.target_site_name, "clear-cache"]
            subprocess.run(clear_cache_cmd, capture_output=True, text=True)
            
            # Rebuild website
            print("Rebuilding website...")
            rebuild_cmd = ["bench", "--site", restore_config.target_site_name, "build"]
            subprocess.run(rebuild_cmd, capture_output=True, text=True)
            
            print("Post-restore tasks completed")
            
        except Exception as e:
            print(f"Warning: Post-restore tasks failed: {e}")