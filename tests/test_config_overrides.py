import os
import pytest
from kvm_mcp_server import _apply_env_overrides, load_config
import json

def test_basic_env_override():
    """Test basic environment variable override"""
    config = {"key": "value"}
    os.environ["KEY"] = "new_value"
    result = _apply_env_overrides(config)
    assert result["key"] == "new_value"
    del os.environ["KEY"]

def test_nested_env_override():
    """Test nested environment variable override"""
    config = {"parent": {"child": "value"}}
    os.environ["PARENT_CHILD"] = "new_value"
    result = _apply_env_overrides(config)
    assert result["parent"]["child"] == "new_value"
    del os.environ["PARENT_CHILD"]

def test_type_conversion():
    """Test type conversion in environment variables"""
    config = {
        "bool_val": True,
        "int_val": 42,
        "float_val": 3.14,
        "str_val": "string"
    }
    
    os.environ.update({
        "BOOL_VAL": "false",
        "INT_VAL": "100",
        "FLOAT_VAL": "2.71",
        "STR_VAL": "new_string"
    })
    
    result = _apply_env_overrides(config)
    assert result["bool_val"] is False
    assert result["int_val"] == 100
    assert result["float_val"] == 2.71
    assert result["str_val"] == "new_string"
    
    # Cleanup
    for key in ["BOOL_VAL", "INT_VAL", "FLOAT_VAL", "STR_VAL"]:
        del os.environ[key]

def test_invalid_conversion():
    """Test handling of invalid type conversions"""
    config = {
        "bool_val": True,
        "int_val": 42,
        "float_val": 3.14
    }
    
    os.environ.update({
        "BOOL_VAL": "invalid",
        "INT_VAL": "not_a_number",
        "FLOAT_VAL": "not_a_float"
    })
    
    result = _apply_env_overrides(config)
    # Should keep original values
    assert result["bool_val"] is True
    assert result["int_val"] == 42
    assert result["float_val"] == 3.14
    
    # Cleanup
    for key in ["BOOL_VAL", "INT_VAL", "FLOAT_VAL"]:
        del os.environ[key]

def test_empty_string_handling():
    """Test handling of empty strings in environment variables"""
    config = {
        "str_val": "original",
        "int_val": 42
    }
    
    os.environ["STR_VAL"] = ""
    result = _apply_env_overrides(config)
    assert result["str_val"] == ""
    assert result["int_val"] == 42
    del os.environ["STR_VAL"]

def test_missing_config_file(tmp_path, monkeypatch):
    """Test handling of missing config file"""
    # Mock os.path.dirname to return our temp path
    monkeypatch.setattr(os.path, 'dirname', lambda x: str(tmp_path))
    monkeypatch.setattr(os.path, 'abspath', lambda x: str(tmp_path))
    
    with pytest.raises(FileNotFoundError):
        load_config()

def test_invalid_json(tmp_path, monkeypatch):
    """Test handling of invalid JSON in config file"""
    # Mock os.path.dirname to return our temp path
    monkeypatch.setattr(os.path, 'dirname', lambda x: str(tmp_path))
    monkeypatch.setattr(os.path, 'abspath', lambda x: str(tmp_path))
    
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        f.write("invalid json")
    
    with pytest.raises(json.JSONDecodeError):
        load_config()

def test_config_with_env_overrides(tmp_path, monkeypatch):
    """Test configuration loading with environment variable overrides"""
    # Mock os.path.dirname to return our temp path
    monkeypatch.setattr(os.path, 'dirname', lambda x: str(tmp_path))
    monkeypatch.setattr(os.path, 'abspath', lambda x: str(tmp_path))
    
    config_content = {
        "vm": {
            "ignition": {
                "default_hostname": "test-vm",
                "default_user": "core",
                "default_timezone": "UTC",
                "default_locale": "en_US.UTF-8",
                "default_ssh_key": "~/.ssh/id_rsa.pub"
            }
        }
    }
    
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_content, f)
    
    os.environ["VM_IGNITION_DEFAULT_HOSTNAME"] = "override-vm"
    os.environ["VM_IGNITION_DEFAULT_USER"] = "admin"
    
    config = load_config()
    
    assert config["vm"]["ignition"]["default_hostname"] == "override-vm"
    assert config["vm"]["ignition"]["default_user"] == "admin"
    assert config["vm"]["ignition"]["default_timezone"] == "UTC"
    assert config["vm"]["ignition"]["default_locale"] == "en_US.UTF-8"
    
    # Cleanup
    del os.environ["VM_IGNITION_DEFAULT_HOSTNAME"]
    del os.environ["VM_IGNITION_DEFAULT_USER"] 