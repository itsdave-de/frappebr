"""Configuration models for FrappeBR."""

from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
from datetime import datetime


class SSHConfig(BaseModel):
    """SSH connection configuration."""
    
    host: str
    hostname: str
    port: int = 22
    user: str
    identity_file: Optional[str] = None
    host_key_alias: Optional[str] = None


class SiteInfo(BaseModel):
    """Frappe site information."""
    
    name: str
    path: str
    bench_path: str
    is_active: bool = True
    apps: List[str] = Field(default_factory=list)
    database_name: str
    size_mb: Optional[float] = None
    last_modified: Optional[datetime] = None


class BackupInfo(BaseModel):
    """Backup file information."""
    
    filename: str
    filepath: str
    site_name: str
    backup_type: str  # 'database', 'files', 'complete'
    created_at: datetime
    size_mb: float
    compressed: bool = True
    md5_hash: Optional[str] = None


class BackupSet(BaseModel):
    """A set of related backup files (e.g., complete backup with multiple files)."""
    
    timestamp: str  # e.g., "20250909_210113"
    site_name: str
    backup_type: str  # 'database', 'files', 'complete'
    created_at: datetime
    total_size_mb: float
    files: List[BackupInfo] = Field(default_factory=list)
    
    @property
    def primary_filename(self) -> str:
        """Get the primary filename to display."""
        # Return database file for complete backups, or first file for others
        for backup_file in self.files:
            if 'database' in backup_file.filename:
                return backup_file.filename
        return self.files[0].filename if self.files else f"{self.timestamp}-{self.site_name}"


class RestoreConfig(BaseModel):
    """Restore operation configuration."""
    
    backup_set: 'BackupSet'
    target_bench_path: str
    target_site_name: str
    mariadb_root_username: str = "root"
    mariadb_root_password: str = ""
    create_new_site: bool = False
    force_restore: bool = True


class AppConfig(BaseModel):
    """Application configuration."""
    
    backup_storage_path: str = "./backups"
    log_level: str = "INFO"
    ssh_timeout: int = 30
    transfer_timeout: int = 3600
    max_concurrent_transfers: int = 3
    compression_level: int = 6
    
    # SSH configuration
    ssh_config_file: str = "~/.ssh/config"
    known_hosts: List[SSHConfig] = Field(default_factory=list)
    
    # Backup retention
    backup_retention_days: int = 30
    auto_cleanup: bool = False