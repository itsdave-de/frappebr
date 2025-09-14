"""Tests for SSH manager functionality."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from frappebr.core.ssh_manager import SSHManager, SSHConnectionError
from frappebr.models.config import SSHConfig


class TestSSHManager:
    """Test SSH manager functionality."""
    
    def test_init(self):
        """Test SSH manager initialization."""
        ssh_manager = SSHManager()
        assert ssh_manager.config_parser is not None
        assert ssh_manager.connections == {}
    
    @patch('frappebr.core.ssh_manager.SSHConfigParser')
    def test_list_hosts(self, mock_parser_class):
        """Test listing SSH hosts."""
        mock_parser = Mock()
        mock_parser.parse_config.return_value = [
            SSHConfig(host="test1", hostname="test1.example.com", user="testuser")
        ]
        mock_parser_class.return_value = mock_parser
        
        ssh_manager = SSHManager()
        hosts = ssh_manager.list_hosts()
        
        assert len(hosts) == 1
        assert hosts[0].host == "test1"
    
    def test_ssh_connection_error(self):
        """Test SSH connection error handling."""
        with pytest.raises(SSHConnectionError):
            raise SSHConnectionError("Test error")
    
    @patch('paramiko.SSHClient')
    def test_connect_success(self, mock_ssh_client):
        """Test successful SSH connection."""
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        ssh_config = SSHConfig(
            host="testhost", 
            hostname="test.example.com", 
            user="testuser"
        )
        
        ssh_manager = SSHManager()
        
        # Mock the config parser to return our test config
        with patch.object(ssh_manager.config_parser, 'get_host_config') as mock_get_config:
            mock_get_config.return_value = ssh_config
            
            result = ssh_manager.connect("testhost")
            
            assert result == mock_client
            mock_client.set_missing_host_key_policy.assert_called_once()
            mock_client.connect.assert_called_once()
    
    def test_file_exists_mock(self):
        """Test file existence check."""
        ssh_manager = SSHManager()
        
        with patch.object(ssh_manager, 'execute_command') as mock_execute:
            mock_execute.return_value = (0, "", "")
            
            result = ssh_manager.file_exists("testhost", "/test/path")
            assert result is True
            
            mock_execute.return_value = (1, "", "")
            result = ssh_manager.file_exists("testhost", "/test/path")
            assert result is False