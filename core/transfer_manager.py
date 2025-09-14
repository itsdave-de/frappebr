"""File transfer management with progress tracking."""

import os
import time
import hashlib
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from threading import Thread, Event
import paramiko

from .ssh_manager import SSHManager, SSHConnectionError
from ..models.config import BackupInfo, BackupSet


class TransferError(Exception):
    """File transfer related errors."""
    pass


class TransferProgress:
    """Track file transfer progress."""
    
    def __init__(self, total_size: int, callback: Optional[Callable] = None):
        self.total_size = total_size
        self.transferred = 0
        self.start_time = time.time()
        self.callback = callback
        self.cancelled = Event()
    
    def update(self, bytes_transferred: int):
        """Update progress."""
        self.transferred += bytes_transferred
        if self.callback and not self.cancelled.is_set():
            self.callback(self)
    
    def cancel(self):
        """Cancel the transfer."""
        self.cancelled.set()
    
    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total_size == 0:
            return 0.0
        return min(100.0, (self.transferred / self.total_size) * 100.0)
    
    @property
    def speed_mbps(self) -> float:
        """Get transfer speed in MB/s."""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return (self.transferred / (1024 * 1024)) / elapsed
    
    @property
    def eta_seconds(self) -> Optional[int]:
        """Get estimated time remaining in seconds."""
        if self.transferred == 0:
            return None
        
        elapsed = time.time() - self.start_time
        rate = self.transferred / elapsed
        remaining_bytes = self.total_size - self.transferred
        
        if rate == 0:
            return None
        
        return int(remaining_bytes / rate)
    
    def format_eta(self) -> str:
        """Format ETA as human-readable string."""
        eta = self.eta_seconds
        if eta is None:
            return "Unknown"
        
        if eta < 60:
            return f"{eta}s"
        elif eta < 3600:
            minutes = eta // 60
            seconds = eta % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = eta // 3600
            minutes = (eta % 3600) // 60
            return f"{hours}h {minutes}m"


class TransferManager:
    """Manages secure file transfers with progress tracking."""
    
    def __init__(self, ssh_manager: SSHManager, local_storage_path: str = "./backups"):
        self.ssh_manager = ssh_manager
        self.local_storage_path = Path(local_storage_path).expanduser().resolve()
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Transfer settings
        self.chunk_size = 32768  # 32KB chunks
        self.max_retries = 3
        self.retry_delay = 5  # seconds
    
    def download_backup(self, hostname: str, backup_info: BackupInfo, 
                       local_filename: Optional[str] = None,
                       progress_callback: Optional[Callable] = None) -> str:
        """Download a backup file from remote host to local storage."""
        if not local_filename:
            local_filename = backup_info.filename
        
        local_path = self.local_storage_path / local_filename
        
        # Check if file already exists and has same size
        if local_path.exists():
            local_size = local_path.stat().st_size
            remote_size = int(backup_info.size_mb * 1024 * 1024)
            
            if local_size == remote_size:
                print(f"File already exists with correct size: {local_path}")
                return str(local_path)
        
        print(f"Downloading {backup_info.filename} to {local_path}")
        
        # Get remote file size
        remote_size = self._get_remote_file_size(hostname, backup_info.filepath)
        if remote_size is None:
            raise TransferError(f"Could not determine size of remote file: {backup_info.filepath}")
        
        # Create progress tracker
        progress = TransferProgress(remote_size, progress_callback)
        
        # Perform the download with retries
        for attempt in range(self.max_retries):
            try:
                self._download_file_with_progress(
                    hostname, backup_info.filepath, local_path, progress
                )
                
                # Verify download
                if self._verify_download(local_path, remote_size):
                    print(f"Download completed successfully: {local_path}")
                    return str(local_path)
                else:
                    raise TransferError("Download verification failed")
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"Download attempt {attempt + 1} failed: {e}")
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    
                    # Remove partial file
                    if local_path.exists():
                        local_path.unlink()
                else:
                    raise TransferError(f"Download failed after {self.max_retries} attempts: {e}")
        
        raise TransferError("Download failed")
    
    def _get_remote_file_size(self, hostname: str, remote_path: str) -> Optional[int]:
        """Get size of remote file in bytes."""
        try:
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'stat -c %s "{remote_path}" 2>/dev/null || stat -f %z "{remote_path}"'
            )
            
            if exit_code == 0 and stdout.strip().isdigit():
                return int(stdout.strip())
        except:
            pass
        
        return None
    
    def _download_file_with_progress(self, hostname: str, remote_path: str, 
                                   local_path: Path, progress: TransferProgress):
        """Download file with progress tracking."""
        try:
            sftp = self.ssh_manager.get_sftp_client(hostname)
            
            def progress_callback(bytes_transferred: int, total_size: int):
                if progress.transferred == 0:
                    progress.update(bytes_transferred)
                else:
                    progress.update(bytes_transferred - progress.transferred)
            
            # Use SFTP get with callback
            sftp.get(remote_path, str(local_path), callback=progress_callback)
            sftp.close()
            
        except Exception as e:
            raise TransferError(f"SFTP transfer failed: {e}")
    
    def _verify_download(self, local_path: Path, expected_size: int) -> bool:
        """Verify downloaded file integrity."""
        if not local_path.exists():
            return False
        
        actual_size = local_path.stat().st_size
        return actual_size == expected_size
    
    def upload_backup(self, hostname: str, local_path: str, remote_path: str,
                     progress_callback: Optional[Callable] = None) -> bool:
        """Upload a backup file to remote host."""
        local_file = Path(local_path)
        if not local_file.exists():
            raise TransferError(f"Local file not found: {local_path}")
        
        local_size = local_file.stat().st_size
        print(f"Uploading {local_file.name} to {hostname}:{remote_path}")
        
        # Create progress tracker
        progress = TransferProgress(local_size, progress_callback)
        
        try:
            sftp = self.ssh_manager.get_sftp_client(hostname)
            
            def progress_callback_wrapper(bytes_transferred: int, total_size: int):
                if progress.transferred == 0:
                    progress.update(bytes_transferred)
                else:
                    progress.update(bytes_transferred - progress.transferred)
            
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self._ensure_remote_directory(sftp, remote_dir)
            
            # Upload file
            sftp.put(str(local_file), remote_path, callback=progress_callback_wrapper)
            sftp.close()
            
            print(f"Upload completed: {remote_path}")
            return True
            
        except Exception as e:
            raise TransferError(f"Upload failed: {e}")
    
    def _ensure_remote_directory(self, sftp: paramiko.SFTPClient, remote_dir: str):
        """Ensure remote directory exists, create if necessary."""
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            # Directory doesn't exist, create it
            parent_dir = os.path.dirname(remote_dir)
            if parent_dir and parent_dir != remote_dir:
                self._ensure_remote_directory(sftp, parent_dir)
            sftp.mkdir(remote_dir)
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """Calculate hash of a local file."""
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(self.chunk_size):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def compare_checksums(self, hostname: str, local_path: str, remote_path: str) -> bool:
        """Compare checksums of local and remote files."""
        try:
            # Calculate local checksum
            local_checksum = self.calculate_file_hash(local_path)
            
            # Get remote checksum
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'md5sum "{remote_path}" 2>/dev/null || md5 -r "{remote_path}"'
            )
            
            if exit_code == 0:
                remote_checksum = stdout.strip().split()[0]
                return local_checksum == remote_checksum
            
        except Exception as e:
            print(f"Checksum comparison failed: {e}")
        
        return False
    
    def resume_download(self, hostname: str, backup_info: BackupInfo, 
                       local_path: Path, progress_callback: Optional[Callable] = None) -> str:
        """Resume an interrupted download."""
        if not local_path.exists():
            # No partial file, start fresh
            return self.download_backup(hostname, backup_info, local_path.name, progress_callback)
        
        # Get sizes
        local_size = local_path.stat().st_size
        remote_size = self._get_remote_file_size(hostname, backup_info.filepath)
        
        if remote_size is None:
            raise TransferError("Could not determine remote file size")
        
        if local_size >= remote_size:
            # File already complete
            if local_size == remote_size:
                print("File already downloaded completely")
                return str(local_path)
            else:
                # Local file is larger, something's wrong
                raise TransferError("Local file is larger than remote file")
        
        print(f"Resuming download from byte {local_size}")
        
        # Create progress tracker starting from current position
        progress = TransferProgress(remote_size, progress_callback)
        progress.transferred = local_size
        
        try:
            sftp = self.ssh_manager.get_sftp_client(hostname)
            
            # Open files for append/resume
            with open(local_path, 'ab') as local_file:
                with sftp.file(backup_info.filepath, 'rb') as remote_file:
                    remote_file.seek(local_size)  # Seek to resume position
                    
                    while True:
                        chunk = remote_file.read(self.chunk_size)
                        if not chunk:
                            break
                        
                        local_file.write(chunk)
                        progress.update(len(chunk))
                        
                        if progress.cancelled.is_set():
                            raise TransferError("Transfer cancelled by user")
            
            sftp.close()
            
            # Verify final size
            if self._verify_download(local_path, remote_size):
                print(f"Resume download completed: {local_path}")
                return str(local_path)
            else:
                raise TransferError("Resume download verification failed")
                
        except Exception as e:
            raise TransferError(f"Resume download failed: {e}")
    
    def get_local_backups(self) -> Dict[str, Dict[str, Any]]:
        """Get information about local backup files."""
        local_backups = {}
        
        for file_path in self.local_storage_path.glob('*'):
            if file_path.is_file():
                stat_info = file_path.stat()
                local_backups[file_path.name] = {
                    'path': str(file_path),
                    'size_mb': round(stat_info.st_size / (1024 * 1024), 2),
                    'modified': stat_info.st_mtime,
                    'md5': self.calculate_file_hash(str(file_path))
                }
        
        return local_backups
    
    def get_local_backup_sets(self) -> Dict[str, BackupSet]:
        """Get local backup files grouped into backup sets."""
        local_backups = self.get_local_backups()
        
        if not local_backups:
            return {}
        
        # Group backups by timestamp
        backup_groups = {}
        for filename, info in local_backups.items():
            # Extract timestamp from filename
            import re
            timestamp_match = re.match(r'(\d{8}_\d{6})', filename)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                if timestamp not in backup_groups:
                    backup_groups[timestamp] = []
                
                # Create BackupInfo object from local file info
                from datetime import datetime
                backup_info = BackupInfo(
                    filename=filename,
                    filepath=info['path'],
                    site_name="unknown",  # Will be parsed from filename
                    backup_type=self._determine_local_backup_type(filename),
                    created_at=datetime.fromtimestamp(info['modified']),
                    size_mb=info['size_mb'],
                    compressed=filename.endswith(('.gz', '.tar', '.tgz')),
                    md5_hash=info['md5']
                )
                backup_groups[timestamp].append(backup_info)
        
        # Create BackupSet objects
        backup_sets = {}
        for timestamp, backup_files in backup_groups.items():
            # Extract site name from filename
            site_name = "unknown"
            for backup_file in backup_files:
                parts = backup_file.filename.split('-')
                if len(parts) >= 2:
                    site_name = parts[1].replace('_', '.')
                    break
            
            # Determine backup set type
            has_database = any('database' in f.filename for f in backup_files)
            has_files = any(f.filename.endswith('.tar') for f in backup_files)
            has_config = any('config' in f.filename for f in backup_files)
            
            if has_database and has_files:
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
            backup_sets[timestamp] = backup_set
        
        return backup_sets
    
    def _determine_local_backup_type(self, filename: str) -> str:
        """Determine backup type from local filename."""
        filename_lower = filename.lower()
        
        if 'database' in filename_lower or filename_lower.endswith('.sql.gz'):
            return 'database'
        elif filename_lower.endswith('.tar') and 'private' in filename_lower:
            return 'private_files'
        elif filename_lower.endswith('.tar'):
            return 'files'
        elif 'config' in filename_lower:
            return 'config'
        else:
            return 'unknown'
    
    def cleanup_local_backups(self, keep_latest: int = 5):
        """Clean up old local backup files, keeping only the latest N files."""
        backups = self.get_local_backups()
        
        if len(backups) <= keep_latest:
            return
        
        # Sort by modification time (newest first)
        sorted_backups = sorted(
            backups.items(), 
            key=lambda x: x[1]['modified'], 
            reverse=True
        )
        
        # Remove old backups
        for filename, info in sorted_backups[keep_latest:]:
            file_path = Path(info['path'])
            try:
                file_path.unlink()
                print(f"Removed old backup: {filename}")
            except Exception as e:
                print(f"Failed to remove {filename}: {e}")