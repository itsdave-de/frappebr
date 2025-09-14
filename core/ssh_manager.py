"""SSH connection management for FrappeBR."""

import os
import paramiko
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager

from ..models.config import SSHConfig
from ..utils.ssh_config import SSHConfigParser


class SSHConnectionError(Exception):
    """SSH connection related errors."""
    pass


class SSHManager:
    """Manages SSH connections to remote hosts."""
    
    def __init__(self, config_file: str = "~/.ssh/config"):
        self.config_parser = SSHConfigParser(config_file)
        self.connections: Dict[str, paramiko.SSHClient] = {}
        
    def list_hosts(self) -> List[SSHConfig]:
        """List all available SSH hosts from config."""
        return self.config_parser.parse_config()
    
    def connect(self, hostname: str, ssh_config: Optional[SSHConfig] = None) -> paramiko.SSHClient:
        """Establish SSH connection to a host."""
        if hostname in self.connections:
            return self.connections[hostname]
        
        if not ssh_config:
            ssh_config = self.config_parser.get_host_config(hostname)
            if not ssh_config:
                raise SSHConnectionError(f"No SSH configuration found for host: {hostname}")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Prepare connection parameters - use SSH agent for key management
            connect_kwargs = {
                'hostname': ssh_config.hostname,
                'port': ssh_config.port,
                'username': ssh_config.user,
                'timeout': 30,
                'compress': True,
                'allow_agent': True,       # Use SSH agent for key management
                'look_for_keys': True,     # Look for keys in standard locations
            }
            
            # Only try to load private key directly if SSH agent fails
            # This allows for passphrase-protected keys via SSH agent
            
            client.connect(**connect_kwargs)
            self.connections[hostname] = client
            return client
            
        except paramiko.AuthenticationException:
            raise SSHConnectionError(f"Authentication failed for {hostname}")
        except paramiko.SSHException as e:
            raise SSHConnectionError(f"SSH connection error to {hostname}: {e}")
        except Exception as e:
            raise SSHConnectionError(f"Failed to connect to {hostname}: {e}")
    
    def disconnect(self, hostname: str):
        """Close SSH connection to a host."""
        if hostname in self.connections:
            self.connections[hostname].close()
            del self.connections[hostname]
    
    def disconnect_all(self):
        """Close all SSH connections."""
        for hostname in list(self.connections.keys()):
            self.disconnect(hostname)
    
    @contextmanager
    def ssh_connection(self, hostname: str, ssh_config: Optional[SSHConfig] = None):
        """Context manager for SSH connections."""
        client = None
        try:
            client = self.connect(hostname, ssh_config)
            yield client
        finally:
            if client and hostname not in self.connections:
                client.close()
    
    def execute_command(self, hostname: str, command: str) -> Tuple[int, str, str]:
        """Execute a command on remote host and return exit code, stdout, stderr."""
        try:
            client = self.connect(hostname)
            stdin, stdout, stderr = client.exec_command(command)
            
            exit_code = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode('utf-8').strip()
            stderr_str = stderr.read().decode('utf-8').strip()
            
            return exit_code, stdout_str, stderr_str
            
        except Exception as e:
            raise SSHConnectionError(f"Command execution failed on {hostname}: {e}")
    
    def test_connection(self, hostname: str, ssh_config: Optional[SSHConfig] = None) -> bool:
        """Test SSH connection to a host."""
        try:
            with self.ssh_connection(hostname, ssh_config) as client:
                # Simple test command
                stdin, stdout, stderr = client.exec_command('echo "test"')
                return stdout.channel.recv_exit_status() == 0
        except Exception:
            return False
    
    def get_sftp_client(self, hostname: str) -> paramiko.SFTPClient:
        """Get SFTP client for file transfers."""
        client = self.connect(hostname)
        return client.open_sftp()
    
    def file_exists(self, hostname: str, remote_path: str) -> bool:
        """Check if a file exists on remote host."""
        try:
            exit_code, _, _ = self.execute_command(hostname, f'test -e "{remote_path}"')
            return exit_code == 0
        except Exception:
            return False
    
    def is_directory(self, hostname: str, remote_path: str) -> bool:
        """Check if a path is a directory on remote host."""
        try:
            exit_code, _, _ = self.execute_command(hostname, f'test -d "{remote_path}"')
            return exit_code == 0
        except Exception:
            return False
    
    def list_directory(self, hostname: str, remote_path: str) -> List[str]:
        """List contents of a directory on remote host."""
        try:
            exit_code, stdout, stderr = self.execute_command(hostname, f'ls -la "{remote_path}"')
            if exit_code == 0:
                return [line.strip() for line in stdout.split('\n') if line.strip()]
            return []
        except Exception:
            return []