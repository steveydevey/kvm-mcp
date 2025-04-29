import pytest
import json
from unittest.mock import patch, mock_open, MagicMock
from kvm_mcp_server import generate_ignition_config

def test_generate_ignition_config_success():
    """Test successful Ignition config generation"""
    vm_name = "test-vm"
    arguments = {
        "hostname": "test-host",
        "user": "test-user",
        "ssh_key": "~/.ssh/test_key.pub",
        "timezone": "America/New_York",
        "locale": "en_US.UTF-8"
    }

    # Mock the SSH key file and os.path.exists
    mock_ssh_key = "ssh-rsa test-key"
    with patch('builtins.open', mock_open(read_data=mock_ssh_key)), \
         patch('os.path.exists', return_value=True):
        config = generate_ignition_config(vm_name, arguments)
        
        # Parse the config to verify its structure
        config_dict = json.loads(config)
        
        # Verify basic structure
        assert config_dict["ignition"]["version"] == "3.3.0"
        assert config_dict["passwd"]["users"][0]["name"] == "test-user"
        assert config_dict["passwd"]["users"][0]["sshAuthorizedKeys"][0] == mock_ssh_key
        assert config_dict["storage"]["files"][0]["contents"]["source"] == "data:,test-host"
        assert config_dict["storage"]["files"][1]["contents"]["source"] == "data:,LANG=en_US.UTF-8"
        assert "timezone.service" in config_dict["systemd"]["units"][0]["name"]

def test_generate_ignition_config_defaults():
    """Test Ignition config generation with default values"""
    vm_name = "test-vm"
    arguments = {}  # Empty arguments should use defaults
    
    # Mock the default SSH key file
    mock_ssh_key = "ssh-rsa default-key"
    with patch('builtins.open', mock_open(read_data=mock_ssh_key)):
        config = generate_ignition_config(vm_name, arguments)
        config_dict = json.loads(config)
        
        # Verify default values are used
        users = config_dict["passwd"]["users"]
        assert users[0]["name"] == "core"  # Default user
        
        hostname_file = next(f for f in config_dict["storage"]["files"] 
                            if f["path"] == "/etc/hostname")
        assert hostname_file["contents"]["source"] == "data:,coreos"  # Default hostname

def test_generate_ignition_config_invalid_ssh_key():
    """Test Ignition config generation with invalid SSH key"""
    vm_name = "test-vm"
    arguments = {
        "ssh_key": "/nonexistent/path/to/key"
    }
    
    with pytest.raises(Exception) as exc_info:
        generate_ignition_config(vm_name, arguments)
    assert "SSH key not found" in str(exc_info.value)

def test_generate_ignition_config_minimal():
    """Test Ignition config generation with minimal parameters"""
    vm_name = "test-vm"
    arguments = {
        "hostname": "minimal-host"
    }
    
    # Mock the default SSH key file
    mock_ssh_key = "ssh-rsa default-key"
    with patch('builtins.open', mock_open(read_data=mock_ssh_key)):
        config = generate_ignition_config(vm_name, arguments)
        config_dict = json.loads(config)
        
        # Verify minimal configuration is valid
        assert "ignition" in config_dict
        assert "passwd" in config_dict
        assert "storage" in config_dict
        assert "systemd" in config_dict
        
        # Verify hostname is set correctly
        hostname_file = next(f for f in config_dict["storage"]["files"] 
                            if f["path"] == "/etc/hostname")
        assert hostname_file["contents"]["source"] == "data:,minimal-host" 