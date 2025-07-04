import pytest
import os
import json
from unittest.mock import patch, mock_open
from kvm_mcp_server import _apply_env_overrides, load_config

def test_load_valid_config():
    """Test loading a valid configuration file"""
    valid_config = {
        "vm": {
            "disk_path": "/vm",
            "default_iso": "/iso/ubuntu.iso",
            "default_master_image": "/iso/fedora.qcow2",
            "default_name": "test-vm",
            "default_memory": 2048,
            "default_vcpus": 2,
            "default_disk_size": 20,
            "default_os_variant": "generic",
            "default_network": "brforvms",
            "ignition": {
                "default_hostname": "coreos",
                "default_user": "core",
                "default_ssh_key": "~/.ssh/id_rsa.pub",
                "default_timezone": "UTC",
                "default_locale": "en_US.UTF-8"
            }
        }
    }
    
    with patch('builtins.open', mock_open(read_data=json.dumps(valid_config))):
        config = load_config()
        assert config == valid_config
        assert "vm" in config
        assert "ignition" in config["vm"]
        assert config["vm"]["default_memory"] == 2048
        assert config["vm"]["default_vcpus"] == 2

def test_missing_config_file():
    """Test handling of missing configuration file"""
    with patch('builtins.open', side_effect=FileNotFoundError("Config file not found")):
        with pytest.raises(FileNotFoundError):
            load_config()

def test_invalid_json():
    """Test handling of invalid JSON in configuration file"""
    invalid_json = "{invalid json}"
    with patch('builtins.open', mock_open(read_data=invalid_json)):
        with pytest.raises(json.JSONDecodeError):
            load_config()

def test_missing_required_fields():
    """Test handling of configuration with missing required fields"""
    incomplete_config = {
        "vm": {
            # Missing required fields
            "ignition": {
                "default_hostname": "coreos"
            }
        }
    }
    
    with patch('builtins.open', mock_open(read_data=json.dumps(incomplete_config))):
        config = load_config()
        # The function should still load the config, but we should test that the code
        # handles missing fields gracefully
        assert "vm" in config
        assert "ignition" in config["vm"]
        assert "default_hostname" in config["vm"]["ignition"]

def test_environment_variable_override():
    """Test that environment variables can override config values"""
    valid_config = {
        "vm": {
            "disk_path": "/vm",
            "default_memory": 2048,
            "ignition": {
                "default_hostname": "coreos"
            }
        }
    }
    
    # Set environment variables with the correct structure
    os.environ["VM_DISK_PATH"] = "/custom/vm"
    os.environ["VM_DEFAULT_MEMORY"] = "4096"
    os.environ["VM_IGNITION_DEFAULT_HOSTNAME"] = "custom-host"
    
    # Debug output
    print("Environment variables:")
    print(f"VM_DISK_PATH: {os.environ.get('VM_DISK_PATH')}")
    print(f"VM_DEFAULT_MEMORY: {os.environ.get('VM_DEFAULT_MEMORY')}")
    print(f"VM_IGNITION_DEFAULT_HOSTNAME: {os.environ.get('VM_IGNITION_DEFAULT_HOSTNAME')}")
    
    with patch('builtins.open', mock_open(read_data=json.dumps(valid_config))):
        config = load_config()
        # Debug output
        print("Loaded config:")
        print(f"disk_path: {config['vm']['disk_path']}")
        print(f"default_memory: {config['vm']['default_memory']}")
        print(f"default_hostname: {config['vm']['ignition']['default_hostname']}")
        
        # The environment variables should override the config values
        assert config["vm"]["disk_path"] == "/custom/vm"
        assert config["vm"]["default_memory"] == 4096
        assert config["vm"]["ignition"]["default_hostname"] == "custom-host"
    
    # Clean up environment variables
    del os.environ["VM_DISK_PATH"]
    del os.environ["VM_DEFAULT_MEMORY"]
    del os.environ["VM_IGNITION_DEFAULT_HOSTNAME"]

def test_config_path_resolution():
    """Test that config file path is resolved correctly"""
    with patch('os.path.join') as mock_join, \
         patch('os.path.dirname') as mock_dirname, \
         patch('os.path.abspath') as mock_abspath, \
         patch('builtins.open', mock_open(read_data='{}')):
        
        mock_abspath.return_value = "/test/path/kvm_mcp_server.py"
        mock_dirname.return_value = "/test/path"
        mock_join.return_value = "/test/path/config.json"
        
        load_config()
        
        # Verify the path was constructed correctly
        mock_abspath.assert_called_once()
        mock_dirname.assert_called_once_with("/test/path/kvm_mcp_server.py")
        mock_join.assert_called_once_with("/test/path", "config.json")

def test_simple_environment_variable_override():
    """Test simple environment variable override"""
    simple_config = {
        "test_key": "default_value",
        "test_number": 42
    }
    
    # Set environment variables
    os.environ["TEST_KEY"] = "override_value"
    os.environ["TEST_NUMBER"] = "100"
    
    with patch('builtins.open', mock_open(read_data=json.dumps(simple_config))):
        config = load_config()
        assert config["test_key"] == "override_value"
        assert config["test_number"] == 100
    
    # Clean up
    del os.environ["TEST_KEY"]
    del os.environ["TEST_NUMBER"]

def test_nested_environment_variable_override():
    """Test nested environment variable override"""
    nested_config = {
        "parent": {
            "child": {
                "value": "default"
            }
        }
    }
    
    # Set environment variable
    os.environ["PARENT_CHILD_VALUE"] = "override"
    
    with patch('builtins.open', mock_open(read_data=json.dumps(nested_config))):
        config = load_config()
        assert config["parent"]["child"]["value"] == "override"
    
    # Clean up
    del os.environ["PARENT_CHILD_VALUE"]

def test_apply_env_overrides_basic():
    """Test basic environment variable overrides"""
    config = {
        "key1": "value1",
        "key2": 42,
        "key3": True
    }
    
    with patch.dict(os.environ, {
        "KEY1": "new_value1",
        "KEY2": "99",
        "KEY3": "false"
    }):
        result = _apply_env_overrides(config)
        assert result["key1"] == "new_value1"
        assert result["key2"] == 99
        assert result["key3"] is False

def test_apply_env_overrides_nested():
    """Test nested configuration overrides"""
    config = {
        "section1": {
            "key1": "value1",
            "key2": 42
        },
        "section2": {
            "key3": True
        }
    }
    
    with patch.dict(os.environ, {
        "SECTION1_KEY1": "new_value1",
        "SECTION1_KEY2": "99",
        "SECTION2_KEY3": "false"
    }):
        result = _apply_env_overrides(config)
        assert result["section1"]["key1"] == "new_value1"
        assert result["section1"]["key2"] == 99
        assert result["section2"]["key3"] is False

def test_apply_env_overrides_invalid_values():
    """Test handling of invalid environment variable values"""
    config = {
        "key1": 42,
        "key2": True,
        "key3": 3.14
    }
    
    with patch.dict(os.environ, {
        "KEY1": "not_a_number",
        "KEY2": "not_a_boolean",
        "KEY3": "not_a_float"
    }):
        result = _apply_env_overrides(config)
        assert result["key1"] == 42  # Original value preserved
        assert result["key2"] is True  # Original value preserved
        assert result["key3"] == 3.14  # Original value preserved

def test_apply_env_overrides_empty_strings():
    """Test handling of empty string values"""
    config = {
        "key1": "value1",
        "key2": 42,
        "key3": True
    }
    
    with patch.dict(os.environ, {
        "KEY1": "",
        "KEY2": "",
        "KEY3": ""
    }):
        result = _apply_env_overrides(config)
        assert result["key1"] == ""  # Empty string allowed for strings
        assert result["key2"] == 42  # Original value preserved for non-strings
        assert result["key3"] is True  # Original value preserved for non-strings

def test_load_config_success():
    """Test successful loading of configuration"""
    config_data = {
        "key1": "value1",
        "key2": 42,
        "key3": True
    }
    
    mock_file = mock_open(read_data=json.dumps(config_data))
    with patch("builtins.open", mock_file):
        result = load_config()
        assert result == config_data

def test_load_config_file_not_found():
    """Test handling of missing configuration file"""
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            load_config()

def test_load_config_invalid_json():
    """Test handling of invalid JSON in configuration file"""
    mock_file = mock_open(read_data="invalid json")
    with patch("builtins.open", mock_file):
        with pytest.raises(json.JSONDecodeError):
            load_config()

def test_load_config_with_env_overrides():
    """Test loading configuration with environment variable overrides"""
    config_data = {
        "key1": "value1",
        "key2": 42,
        "key3": True
    }
    
    mock_file = mock_open(read_data=json.dumps(config_data))
    with patch("builtins.open", mock_file), \
         patch.dict(os.environ, {"KEY1": "new_value1"}):
        result = load_config()
        assert result["key1"] == "new_value1"
        assert result["key2"] == 42
        assert result["key3"] is True 