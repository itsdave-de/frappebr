"""SSH configuration parsing utilities."""

import os
from pathlib import Path
from typing import Dict, List, Optional
from ..models.config import SSHConfig


class SSHConfigParser:
    """Parse SSH configuration files."""
    
    def __init__(self, config_file: str = "~/.ssh/config"):
        self.config_file = Path(config_file).expanduser()
    
    def parse_config(self) -> List[SSHConfig]:
        """Parse SSH config file and return list of host configurations."""
        if not self.config_file.exists():
            return []
        
        hosts = []
        current_host = {}
        
        try:
            with open(self.config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.lower().startswith('host '):
                        if current_host and 'host' in current_host:
                            hosts.append(self._create_ssh_config(current_host))
                        
                        host_names = line[5:].strip().split()
                        current_host = {'host': host_names[0]}
                        if len(host_names) == 1:
                            current_host['hostname'] = host_names[0]
                    
                    elif current_host:
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            key, value = parts
                            key = key.lower()
                            
                            if key == 'hostname':
                                current_host['hostname'] = value
                            elif key == 'port':
                                current_host['port'] = int(value)
                            elif key == 'user':
                                current_host['user'] = value
                            elif key == 'identityfile':
                                current_host['identity_file'] = str(Path(value).expanduser())
                            elif key == 'hostkeyalias':
                                current_host['host_key_alias'] = value
                
                # Don't forget the last host
                if current_host and 'host' in current_host:
                    hosts.append(self._create_ssh_config(current_host))
        
        except Exception as e:
            print(f"Error parsing SSH config: {e}")
            return []
        
        return hosts
    
    def _create_ssh_config(self, config_dict: Dict) -> SSHConfig:
        """Create SSHConfig object from dictionary."""
        # Set defaults if not provided
        if 'hostname' not in config_dict:
            config_dict['hostname'] = config_dict['host']
        if 'port' not in config_dict:
            config_dict['port'] = 22
        if 'user' not in config_dict:
            config_dict['user'] = os.getenv('USER', 'root')
        
        return SSHConfig(**config_dict)
    
    def get_host_config(self, hostname: str) -> Optional[SSHConfig]:
        """Get configuration for a specific host."""
        configs = self.parse_config()
        for config in configs:
            if config.host == hostname or config.hostname == hostname:
                return config
        return None