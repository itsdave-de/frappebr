"""Frappe backup management functionality."""

import os
import re
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime

from .ssh_manager import SSHManager, SSHConnectionError
from ..models.config import BackupInfo, BackupSet, SiteInfo


class BackupError(Exception):
    """Backup related errors."""
    pass


class BackupManager:
    """Manages Frappe site backups."""
    
    def __init__(self, ssh_manager: SSHManager):
        self.ssh_manager = ssh_manager
    
    def list_backups(self, hostname: str, bench_path: str, site_name: str) -> List[BackupInfo]:
        """List all available backups for a site."""
        backup_path = f"{bench_path}/sites/{site_name}/private/backups"
        
        # Check if backup directory exists
        if not self.ssh_manager.is_directory(hostname, backup_path):
            return []
        
        backups = []
        
        try:
            # List all files in backup directory
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'ls -la "{backup_path}"'
            )
            
            if exit_code != 0:
                return backups
            
            for line in stdout.split('\n'):
                if not line.strip() or line.startswith('total'):
                    continue
                
                parts = line.split()
                if len(parts) < 9 or parts[0].startswith('d'):
                    continue
                
                filename = parts[-1]
                
                # Skip non-backup files
                if not self._is_backup_file(filename):
                    continue
                
                filepath = f"{backup_path}/{filename}"
                backup_info = self._parse_backup_info(hostname, filepath, filename, site_name)
                
                if backup_info:
                    backups.append(backup_info)
        
        except Exception as e:
            raise BackupError(f"Failed to list backups for {site_name}: {e}")
        
        # Sort by creation date (newest first)
        return sorted(backups, key=lambda x: x.created_at, reverse=True)
    
    def _is_backup_file(self, filename: str) -> bool:
        """Check if a file is a backup file."""
        backup_extensions = ['.sql.gz', '.tar', '.tar.gz', '.tgz']
        return any(filename.endswith(ext) for ext in backup_extensions)
    
    def _parse_backup_info(self, hostname: str, filepath: str, filename: str, site_name: str) -> Optional[BackupInfo]:
        """Parse backup file information."""
        try:
            # Get file stats
            stat_command = 'stat -c "%s %Y" "{}" 2>/dev/null || stat -f "%z %m" "{}"'.format(filepath, filepath)
            exit_code, stdout, _ = self.ssh_manager.execute_command(hostname, stat_command)
            
            if exit_code != 0:
                return None
            
            stat_parts = stdout.strip().split()
            if len(stat_parts) < 2:
                return None
            
            size_bytes = int(stat_parts[0])
            timestamp = int(stat_parts[1])
            
            size_mb = round(size_bytes / (1024 * 1024), 2)
            created_at = datetime.fromtimestamp(timestamp)
            
            # Determine backup type from filename
            backup_type = self._determine_backup_type(filename)
            
            # Check if compressed
            compressed = filename.endswith(('.gz', '.tar', '.tgz'))
            
            return BackupInfo(
                filename=filename,
                filepath=filepath,
                site_name=site_name,
                backup_type=backup_type,
                created_at=created_at,
                size_mb=size_mb,
                compressed=compressed,
                md5_hash=None  # We'll calculate this during transfer
            )
        
        except Exception as e:
            print(f"Error parsing backup info for {filename}: {e}")
            return None
    
    def _determine_backup_type(self, filename: str) -> str:
        """Determine backup type from filename."""
        filename_lower = filename.lower()
        
        if 'database' in filename_lower or filename_lower.endswith('.sql.gz'):
            return 'database'
        elif 'files' in filename_lower and not 'database' in filename_lower:
            return 'files'
        else:
            return 'complete'
    
    def create_backup(self, hostname: str, bench_path: str, site_name: str, 
                     backup_type: str = 'complete', with_files: bool = True) -> BackupInfo:
        """Create a new backup for a site."""
        if not self._validate_bench_and_site(hostname, bench_path, site_name):
            raise BackupError(f"Invalid bench or site: {bench_path}/{site_name}")
        
        try:
            # Change to bench directory and run bench command with full path
            # This is crucial - bench must be run FROM the bench directory
            bench_cmd = '/home/itsdave/.local/bin/bench'  # Use absolute path instead of ~
            if backup_type == 'database':
                command = f'cd "{bench_path}" && {bench_cmd} --site {site_name} backup --only-db'
            elif backup_type == 'files':
                command = f'cd "{bench_path}" && {bench_cmd} --site {site_name} backup --only-files'
            else:  # complete backup
                files_flag = '--with-files' if with_files else ''
                command = f'cd "{bench_path}" && {bench_cmd} --site {site_name} backup {files_flag}'
            
            print(f"Creating {backup_type} backup for {site_name}...")
            exit_code, stdout, stderr = self.ssh_manager.execute_command(hostname, command)
            
            if exit_code != 0:
                raise BackupError(f"Backup creation failed: {stderr}")
            
            # Parse output to find the created backup file
            backup_file = self._extract_backup_filename(stdout, stderr)
            if not backup_file:
                # If we can't parse the filename, the backup was still created
                # Just inform the user and let them use the backup list to see it
                print("Backup created successfully, but could not determine filename.")
                print("The backup is available in the backup list.")
                return None
            
            # Get backup info
            backup_path = f"{bench_path}/sites/{site_name}/private/backups"
            full_backup_path = f"{backup_path}/{backup_file}"
            
            backup_info = self._parse_backup_info(hostname, full_backup_path, backup_file, site_name)
            if not backup_info:
                raise BackupError("Could not parse backup information")
            
            print(f"Backup created successfully: {backup_file}")
            return backup_info
        
        except SSHConnectionError as e:
            raise BackupError(f"SSH error during backup creation: {e}")
        except Exception as e:
            raise BackupError(f"Failed to create backup: {e}")
    
    def _extract_backup_filename(self, stdout: str, stderr: str) -> Optional[str]:
        """Extract backup filename from bench command output."""
        output = stdout + stderr
        
        # Debug: print the actual output to help with troubleshooting
        print(f"DEBUG - Bench command output:\n{output}")
        
        # Look for all backup files in the bench output
        backup_files = []
        patterns = [
            r'Config\s*:\s*([^\s]+)',    # Matches "Config  : /path/to/file.json"
            r'Database:\s*([^\s]+)',     # Matches "Database: /path/to/file.sql.gz"
            r'Public\s*:\s*([^\s]+)',    # Matches "Public  : /path/to/file.tar"
            r'Private\s*:\s*([^\s]+)',   # Matches "Private : /path/to/file.tar"
        ]
        
        # Collect all backup files
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                backup_path = match.group(1).strip()
                backup_files.append(os.path.basename(backup_path))
        
        if backup_files:
            print(f"DEBUG - Found backup files: {backup_files}")
            # Return the database backup as primary (for compatibility)
            for filename in backup_files:
                if 'database' in filename:
                    return filename
            # If no database file, return the first one
            return backup_files[0]
        
        # Fallback: look for any .sql.gz or .tar files mentioned
        sql_match = re.search(r'(\w+_\d{8}_\d{6}_database\.sql\.gz)', output)
        if sql_match:
            return sql_match.group(1)
        
        tar_match = re.search(r'(\w+_\d{8}_\d{6}_files\.tar)', output)
        if tar_match:
            return tar_match.group(1)
        
        # Final fallback: if parsing fails but backup was created successfully,
        # find the most recently created backup file
        print("DEBUG - Regex parsing failed, trying fallback method...")
        return None
    
    def get_backup_set_files(self, hostname: str, backup_info: BackupInfo) -> List[BackupInfo]:
        """Get all related backup files for a backup set (e.g., complete backup with multiple files)."""
        # Extract the timestamp from the backup filename
        # e.g., "20250909_210113-frappe15_labexposed_com-database.sql.gz" -> "20250909_210113"
        import re
        timestamp_match = re.match(r'(\d{8}_\d{6})', backup_info.filename)
        if not timestamp_match:
            return [backup_info]  # Return just the original if we can't parse timestamp
        
        timestamp = timestamp_match.group(1)
        site_prefix = backup_info.filename.split('-')[1]  # e.g., "frappe15_labexposed_com"
        
        # List all backups and find ones with same timestamp
        all_backups = self.list_backups(hostname, 
                                       os.path.dirname(backup_info.filepath.replace(f'/sites/{backup_info.site_name}/private/backups', '')),
                                       backup_info.site_name)
        
        related_backups = []
        for backup in all_backups:
            if backup.filename.startswith(f"{timestamp}-{site_prefix}"):
                related_backups.append(backup)
        
        return related_backups if related_backups else [backup_info]
    
    def list_backup_sets(self, hostname: str, bench_path: str, site_name: str) -> List[BackupSet]:
        """List backups grouped by backup sets for better UI display."""
        # Get all individual backup files
        all_backups = self.list_backups(hostname, bench_path, site_name)
        
        # Group backups by timestamp
        backup_groups = {}
        for backup in all_backups:
            # Extract timestamp from filename
            timestamp_match = re.match(r'(\d{8}_\d{6})', backup.filename)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                if timestamp not in backup_groups:
                    backup_groups[timestamp] = []
                backup_groups[timestamp].append(backup)
        
        # Create BackupSet objects
        backup_sets = []
        for timestamp, backup_files in backup_groups.items():
            # Determine backup set type
            has_database = any('database' in f.filename for f in backup_files)
            has_files = any(f.filename.endswith('.tar') for f in backup_files)
            has_config = any('config' in f.filename for f in backup_files)
            
            if has_database and has_files and has_config:
                backup_type = 'complete'
            elif has_database and not has_files:
                backup_type = 'database'
            elif has_files and not has_database:
                backup_type = 'files'
            else:
                backup_type = 'mixed'
            
            # Calculate total size
            total_size = sum(f.size_mb for f in backup_files)
            
            # Use the latest creation time
            latest_time = max(f.created_at for f in backup_files)
            
            backup_set = BackupSet(
                timestamp=timestamp,
                site_name=site_name,
                backup_type=backup_type,
                created_at=latest_time,
                total_size_mb=total_size,
                files=backup_files
            )
            backup_sets.append(backup_set)
        
        # Sort by creation date (newest first)
        return sorted(backup_sets, key=lambda x: x.created_at, reverse=True)
    
    def _validate_bench_and_site(self, hostname: str, bench_path: str, site_name: str) -> bool:
        """Validate that bench and site exist and are accessible."""
        # Check bench directory
        if not self.ssh_manager.is_directory(hostname, bench_path):
            return False
        
        # Check sites directory
        sites_path = f"{bench_path}/sites"
        if not self.ssh_manager.is_directory(hostname, sites_path):
            return False
        
        # Check site directory
        site_path = f"{sites_path}/{site_name}"
        if not self.ssh_manager.is_directory(hostname, site_path):
            return False
        
        # Check site config
        config_path = f"{site_path}/site_config.json"
        return self.ssh_manager.file_exists(hostname, config_path)
    
    def delete_backup(self, hostname: str, backup_info: BackupInfo) -> bool:
        """Delete a backup file."""
        try:
            exit_code, _, stderr = self.ssh_manager.execute_command(
                hostname, f'rm -f "{backup_info.filepath}"'
            )
            
            if exit_code == 0:
                print(f"Backup deleted: {backup_info.filename}")
                return True
            else:
                print(f"Failed to delete backup: {stderr}")
                return False
        
        except Exception as e:
            print(f"Error deleting backup: {e}")
            return False
    
    def get_backup_size(self, hostname: str, backup_path: str) -> Optional[int]:
        """Get backup file size in bytes."""
        try:
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'stat -c %s "{backup_path}" 2>/dev/null || stat -f %z "{backup_path}"'
            )
            
            if exit_code == 0 and stdout.strip().isdigit():
                return int(stdout.strip())
        except:
            pass
        
        return None
    
    def calculate_md5(self, hostname: str, backup_path: str) -> Optional[str]:
        """Calculate MD5 hash of backup file."""
        try:
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'md5sum "{backup_path}" 2>/dev/null || md5 -r "{backup_path}"'
            )
            
            if exit_code == 0:
                # Parse output (format differs between md5sum and md5)
                parts = stdout.strip().split()
                if parts:
                    return parts[0]
        except:
            pass
        
        return None
    
    def verify_backup_integrity(self, hostname: str, backup_info: BackupInfo) -> bool:
        """Verify backup file integrity."""
        try:
            # Check if file exists
            if not self.ssh_manager.file_exists(hostname, backup_info.filepath):
                return False
            
            # Check if file is not empty
            size = self.get_backup_size(hostname, backup_info.filepath)
            if not size or size == 0:
                return False
            
            # For compressed files, try to test the archive
            if backup_info.compressed:
                if backup_info.filename.endswith('.gz'):
                    exit_code, _, _ = self.ssh_manager.execute_command(
                        hostname, f'gzip -t "{backup_info.filepath}"'
                    )
                    return exit_code == 0
                elif backup_info.filename.endswith(('.tar', '.tgz')):
                    exit_code, _, _ = self.ssh_manager.execute_command(
                        hostname, f'tar -tf "{backup_info.filepath}" > /dev/null'
                    )
                    return exit_code == 0
            
            return True
        
        except Exception:
            return False