"""Frappe site discovery and management."""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from .ssh_manager import SSHManager, SSHConnectionError
from ..models.config import SiteInfo


class SiteDiscoveryError(Exception):
    """Site discovery related errors."""
    pass


class SiteManager:
    """Manages Frappe site discovery and operations."""
    
    def __init__(self, ssh_manager: SSHManager):
        self.ssh_manager = ssh_manager
    
    def find_frappe_benches(self, hostname: str, search_paths: Optional[List[str]] = None) -> List[str]:
        """Find all frappe-bench directories on a host."""
        if not search_paths:
            search_paths = [
                "/home/*/frappe-bench",
                "/home/*/frappe-*",        # Match frappe-15, frappe-dev, etc.
                "/opt/bench/*/frappe-bench", 
                "/opt/bench/*/frappe-*",
                "/var/www/*/frappe-bench",
                "/var/www/*/frappe-*",
                "~/frappe-bench",
                "~/frappe-*",              # User home frappe directories
                "/home/frappe/frappe-*",   # Common frappe user setup
                "/home/itsdave/frappe-*"   # Your specific setup
            ]
        
        bench_paths = []
        
        for search_path in search_paths:
            try:
                # Use find command to locate frappe directories
                if "frappe-*" in search_path:
                    # For wildcard patterns, use glob-style find
                    base_path = search_path.replace("/frappe-*", "")
                    command = f'find {base_path} -maxdepth 1 -name "frappe-*" -type d 2>/dev/null || true'
                else:
                    # For specific patterns, use exact match
                    command = f'find {search_path} -maxdepth 2 -name "frappe-bench" -type d 2>/dev/null || true'
                exit_code, stdout, _ = self.ssh_manager.execute_command(hostname, command)
                
                if exit_code == 0 and stdout:
                    for path in stdout.split('\n'):
                        path = path.strip()
                        if path and self._is_valid_frappe_bench(hostname, path):
                            bench_paths.append(path)
            
            except SSHConnectionError:
                continue
        
        # Remove duplicates and sort
        return sorted(list(set(bench_paths)))
    
    def _is_valid_frappe_bench(self, hostname: str, bench_path: str) -> bool:
        """Check if a directory is a valid frappe-bench."""
        required_files = [
            "sites",
            "apps", 
            "sites/common_site_config.json"  # This is the correct location
        ]
        
        for file_path in required_files:
            full_path = f"{bench_path}/{file_path}"
            if not self.ssh_manager.file_exists(hostname, full_path):
                return False
        
        return True
    
    def list_sites(self, hostname: str, bench_path: str) -> List[SiteInfo]:
        """List all sites in a frappe-bench."""
        if not self._is_valid_frappe_bench(hostname, bench_path):
            raise SiteDiscoveryError(f"Invalid frappe-bench path: {bench_path}")
        
        sites = []
        sites_path = f"{bench_path}/sites"
        
        try:
            # List all directories in sites folder
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'ls -la "{sites_path}"'
            )
            
            if exit_code != 0:
                return sites
            
            for line in stdout.split('\n'):
                if not line.strip() or line.startswith('total'):
                    continue
                
                parts = line.split()
                if len(parts) < 9 or parts[0].startswith('d') == False:
                    continue
                
                site_name = parts[-1]
                
                # Skip system directories
                if site_name in ['.', '..', 'apps.txt', 'common_site_config.json']:
                    continue
                
                site_path = f"{sites_path}/{site_name}"
                
                # Check if it's a valid site (has site_config.json)
                config_path = f"{site_path}/site_config.json"
                if self.ssh_manager.file_exists(hostname, config_path):
                    site_info = self._get_site_info(hostname, bench_path, site_name)
                    if site_info:
                        sites.append(site_info)
        
        except Exception as e:
            raise SiteDiscoveryError(f"Failed to list sites in {bench_path}: {e}")
        
        return sites
    
    def _get_site_info(self, hostname: str, bench_path: str, site_name: str) -> Optional[SiteInfo]:
        """Get detailed information about a site."""
        try:
            site_path = f"{bench_path}/sites/{site_name}"
            config_path = f"{site_path}/site_config.json"
            
            # Read site configuration
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'cat "{config_path}"'
            )
            
            if exit_code != 0:
                return None
            
            try:
                site_config = json.loads(stdout)
            except json.JSONDecodeError:
                return None
            
            # Get database name
            db_name = site_config.get('db_name', f'{site_name.replace(".", "_")}_db')
            
            # Check if site is active (has current symlink or is accessible)
            is_active = self._is_site_active(hostname, bench_path, site_name)
            
            # Get installed apps
            apps = self._get_installed_apps(hostname, site_path)
            
            # Get site size
            size_mb = self._get_site_size(hostname, site_path)
            
            # Get last modified date
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'stat -c %Y "{config_path}" 2>/dev/null || stat -f %m "{config_path}" 2>/dev/null || echo "0"'
            )
            
            last_modified = None
            if exit_code == 0 and stdout.strip().isdigit():
                timestamp = int(stdout.strip())
                if timestamp > 0:
                    last_modified = datetime.fromtimestamp(timestamp)
            
            return SiteInfo(
                name=site_name,
                path=site_path,
                bench_path=bench_path,
                is_active=is_active,
                apps=apps,
                database_name=db_name,
                size_mb=size_mb,
                last_modified=last_modified
            )
        
        except Exception as e:
            print(f"Error getting site info for {site_name}: {e}")
            return None
    
    def _is_site_active(self, hostname: str, bench_path: str, site_name: str) -> bool:
        """Check if a site is currently active."""
        try:
            # Try to run bench status command
            command = f'cd "{bench_path}" && bench --site {site_name} list-apps --format json'
            exit_code, _, _ = self.ssh_manager.execute_command(hostname, command)
            return exit_code == 0
        except:
            return True  # Assume active if we can't determine
    
    def _get_installed_apps(self, hostname: str, site_path: str) -> List[str]:
        """Get list of installed apps for a site."""
        try:
            apps_file = f"{site_path}/apps.txt"
            if not self.ssh_manager.file_exists(hostname, apps_file):
                return []
            
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'cat "{apps_file}"'
            )
            
            if exit_code == 0:
                return [app.strip() for app in stdout.split('\n') if app.strip()]
        except:
            pass
        
        return []
    
    def _get_site_size(self, hostname: str, site_path: str) -> Optional[float]:
        """Get site directory size in MB."""
        try:
            # Use du command to get size in KB, then convert to MB
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'du -sk "{site_path}" 2>/dev/null | cut -f1'
            )
            
            if exit_code == 0 and stdout.strip().isdigit():
                size_kb = int(stdout.strip())
                return round(size_kb / 1024.0, 2)  # Convert KB to MB
        except:
            pass
        
        return None
    
    def get_site_config(self, hostname: str, site_path: str) -> Dict[str, Any]:
        """Get site configuration as dictionary."""
        config_path = f"{site_path}/site_config.json"
        
        try:
            exit_code, stdout, _ = self.ssh_manager.execute_command(
                hostname, f'cat "{config_path}"'
            )
            
            if exit_code == 0:
                return json.loads(stdout)
        except Exception as e:
            raise SiteDiscoveryError(f"Failed to read site config from {config_path}: {e}")
        
        return {}
    
    def validate_site(self, hostname: str, bench_path: str, site_name: str) -> bool:
        """Validate that a site exists and is properly configured."""
        site_path = f"{bench_path}/sites/{site_name}"
        required_files = [
            f"{site_path}/site_config.json",
            f"{bench_path}/config/common_site_config.json"
        ]
        
        for file_path in required_files:
            if not self.ssh_manager.file_exists(hostname, file_path):
                return False
        
        return True