import pytest
from unittest.mock import patch, MagicMock, mock_open
import libvirt
from kvm_mcp_server import create_vm, start_vm, stop_vm, reboot_vm, generate_ignition_config, get_vnc_ports, _apply_env_overrides, handle_request, load_config
import json
import subprocess
import os

@pytest.mark.asyncio
async def test_create_vm_zero_resources():
    """Test creating a VM with zero memory and vcpus"""
    with patch('libvirt.open') as mock_open, \
         patch('subprocess.run') as mock_run:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        mock_conn.lookupByName.side_effect = libvirt.libvirtError('Domain not found')
        mock_run.return_value = MagicMock(returncode=0)
        
        result = await create_vm("create_vm", {
            "name": "test-vm",
            "memory": 0,
            "vcpus": 0,
            "disk_size": 0,
            "master_image": "/some/image.qcow2"  # Need this to avoid disk_path error
        })
        
        assert result["status"] == "error"
        assert any(x in result["message"].lower() for x in ["invalid", "memory", "vcpu", "resources"])

@pytest.mark.asyncio
async def test_create_vm_special_chars():
    """Test creating a VM with special characters in name"""
    with patch('libvirt.open') as mock_open, \
         patch('subprocess.run') as mock_run:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        mock_conn.lookupByName.side_effect = libvirt.libvirtError('Domain not found')
        mock_run.return_value = MagicMock(returncode=0)
        
        result = await create_vm("create_vm", {
            "name": "test!@#$%^&*()",
            "memory": 2048,
            "vcpus": 2,
            "master_image": "/some/image.qcow2"  # Need this to avoid disk_path error
        })
        
        assert result["status"] == "error"
        assert any(x in result["message"].lower() for x in ["invalid", "name", "character"])

@pytest.mark.asyncio
async def test_create_vm_extremely_large_resources():
    """Test creating a VM with extremely large resource values"""
    with patch('libvirt.open') as mock_open, \
         patch('subprocess.run') as mock_run:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        mock_conn.lookupByName.side_effect = libvirt.libvirtError('Domain not found')
        mock_run.return_value = MagicMock(returncode=0)
        
        result = await create_vm("create_vm", {
            "name": "test-vm",
            "memory": 1024 * 1024 * 1024,  # Extremely large memory
            "vcpus": 1000,  # Extremely large number of vcpus
            "disk_size": 1000000,  # Extremely large disk
            "master_image": "/some/image.qcow2"  # Need this to avoid disk_path error
        })
        
        assert result["status"] == "error"
        assert any(x in result["message"].lower() for x in ["memory", "vcpu", "disk", "resources", "large"])

@pytest.mark.asyncio
async def test_vm_operations_null_domain(mock_libvirt_conn):
    """Test VM operations when domain object is None"""
    with patch('libvirt.open') as mock_open:
        # Set up the mock connection
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError('Domain not found')
        mock_open.return_value = mock_libvirt_conn
        
        for operation in [start_vm, stop_vm, reboot_vm]:
            result = await operation("operation", {"name": "test-vm"})
            assert result["status"] == "error"
            assert "not found" in result["message"].lower()

@pytest.mark.asyncio
async def test_vm_operations_connection_timeout(mock_libvirt_conn):
    """Test VM operations when connection times out"""
    with patch('libvirt.open') as mock_open:
        mock_open.side_effect = libvirt.libvirtError('Connection timed out')
        
        for operation in [start_vm, stop_vm, reboot_vm]:
            result = await operation("operation", {"name": "test-vm"})
            assert result["status"] == "error"
            assert "timed out" in result["message"].lower()

@pytest.mark.asyncio
async def test_create_vm_with_invalid_master_image(mock_libvirt_conn):
    """Test creating a VM with non-existent master image"""
    with patch('libvirt.open') as mock_open, \
         patch('subprocess.run') as mock_run:
        mock_open.return_value = mock_libvirt_conn
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError('Domain not found')
        mock_run.side_effect = subprocess.CalledProcessError(1, 'qemu-img', 
            'Failed to open master image')
        
        result = await create_vm("create_vm", {
            "name": "test-vm",
            "memory": 2048,
            "vcpus": 2,
            "master_image": "/nonexistent/image.qcow2"
        })
        
        assert result["status"] == "error"
        assert any(x in result["message"].lower() for x in ["master image", "failed", "qemu-img"])

def test_generate_ignition_config_empty_values():
    """Test generating Ignition config with empty string values"""
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data="ssh-key")):
        with pytest.raises(ValueError, match=r"Empty values are not allowed for hostname, user, timezone, or locale"):
            generate_ignition_config("test-vm", {
                "hostname": "",
                "user": "",
                "timezone": "",
                "locale": ""
            })

def test_generate_ignition_config_very_long_values():
    """Test generating Ignition config with very long input values"""
    long_string = "a" * 1000  # 1000 character string
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data="ssh-key")):
        config = generate_ignition_config("test-vm", {
            "hostname": long_string,
            "user": long_string,
            "timezone": long_string,
            "locale": long_string
        })
        
        config_dict = json.loads(config)
        assert config_dict["ignition"]["version"] == "3.3.0"
        # Verify the config can be generated with long values
        assert "hostname" in str(config_dict["storage"]["files"])

@pytest.mark.asyncio
async def test_get_vnc_ports_no_running_vms():
    """Test getting VNC ports when no VMs are running"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        result = await get_vnc_ports("get_vnc_ports", {})
        assert result["status"] == "success"
        assert len(result["vnc_ports"]) == 0

@pytest.mark.asyncio
async def test_get_vnc_ports_virsh_error():
    """Test getting VNC ports when virsh command fails"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="virsh command failed"
        )
        
        result = await get_vnc_ports("get_vnc_ports", {})
        assert result["status"] == "error"
        assert "Failed to get VM list" in result["message"]

@pytest.mark.asyncio
async def test_get_vnc_ports_invalid_display():
    """Test getting VNC ports with invalid display numbers"""
    with patch('subprocess.run') as mock_run:
        def mock_run_command(cmd, **kwargs):
            if cmd[1] == 'list':
                return MagicMock(returncode=0, stdout="test-vm\n")
            elif cmd[1] == 'vncdisplay':
                return MagicMock(returncode=0, stdout="invalid:display\n")
        
        mock_run.side_effect = mock_run_command
        
        result = await get_vnc_ports("get_vnc_ports", {})
        assert result["status"] == "success"
        assert "test-vm" not in result["vnc_ports"]

def test_env_override_invalid_types():
    """Test environment variable overrides with invalid type conversions"""
    config = {
        "int_value": 42,
        "float_value": 3.14,
        "bool_value": True
    }
    
    with patch.dict(os.environ, {
        "INT_VALUE": "not_an_int",
        "FLOAT_VALUE": "not_a_float",
        "BOOL_VALUE": "not_a_bool"
    }):
        _apply_env_overrides(config)
        # Original values should be preserved when conversion fails
        assert config["int_value"] == 42
        assert config["float_value"] == 3.14
        assert config["bool_value"] == True

def test_env_override_nested_special_chars():
    """Test environment variable overrides with special characters in nested paths"""
    config = {
        "level1": {
            "level!2": {
                "level@3": "value"
            }
        }
    }
    
    with patch.dict(os.environ, {
        "LEVEL1_LEVEL!2_LEVEL@3": "new_value"
    }):
        _apply_env_overrides(config)
        assert config["level1"]["level!2"]["level@3"] == "new_value"

def test_env_override_empty_values():
    """Test environment variable overrides with empty values"""
    config = {
        "string_value": "original",
        "int_value": 42,
        "bool_value": True
    }
    
    with patch.dict(os.environ, {
        "STRING_VALUE": "",
        "INT_VALUE": "",
        "BOOL_VALUE": ""
    }):
        _apply_env_overrides(config)
        # Empty values should not override existing values
        assert config["string_value"] == ""  # Strings can be empty
        assert config["int_value"] == 42  # Numbers should keep original
        assert config["bool_value"] == True  # Booleans should keep original

@pytest.mark.asyncio
async def test_invalid_json_input():
    """Test handling of invalid JSON input"""
    response = await handle_request("invalid json")
    assert response["jsonrpc"] == "2.0"
    assert response["error"]["code"] == -32700
    assert "Parse error" in response["error"]["message"]

@pytest.mark.asyncio
async def test_missing_method():
    """Test handling of request with missing method"""
    request = {
        "jsonrpc": "2.0",
        "id": 1
    }
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]

@pytest.mark.asyncio
async def test_unknown_method():
    """Test handling of unknown method"""
    request = {
        "jsonrpc": "2.0",
        "method": "unknown_method",
        "id": 1
    }
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]

@pytest.mark.asyncio
async def test_invalid_tool_name():
    """Test handling of invalid tool name in tools/call"""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "invalid_tool",
            "arguments": {}
        },
        "id": 1
    }
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]

@pytest.mark.asyncio
async def test_create_vm_invalid_name():
    """Test VM creation with invalid name"""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "create_vm",
            "arguments": {
                "name": "invalid@name",
                "memory": 2048,
                "vcpus": 2
            }
        },
        "id": 1
    }
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert "error" in response
    assert response["error"]["code"] == -32603
    assert "VM name contains invalid characters" in response["error"]["message"]

@pytest.mark.asyncio
async def test_create_vm_resource_limits():
    """Test VM creation with resource limits"""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "create_vm",
            "arguments": {
                "name": "test-vm",
                "memory": 1024 * 1024 + 1,  # Exceeds 1TB limit
                "vcpus": 129,  # Exceeds 128 vCPU limit
                "disk_size": 10001  # Exceeds 10TB limit
            }
        },
        "id": 1
    }
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert "error" in response
    assert response["error"]["code"] == -32603
    assert any(x in response["error"]["message"].lower() for x in ["memory exceeds", "vcpus exceed", "disk size exceeds"])

@pytest.mark.asyncio
async def test_libvirt_connection_failure(mock_libvirt_conn):
    """Test handling of libvirt connection failure"""
    with patch('libvirt.open') as mock_open:
        mock_open.return_value = None
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_vms",
                "arguments": {}
            },
            "id": 1
        }
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert response["result"][0]["error"] == "Failed to connect to libvirt daemon"

def test_env_overrides():
    """Test environment variable overrides"""
    config = {
        "vm": {
            "memory": 2048,
            "vcpus": 2,
            "disk_size": 20.0  # Changed to float
        }
    }
    
    # Test integer override
    os.environ["VM_MEMORY"] = "4096"
    _apply_env_overrides(config)
    assert config["vm"]["memory"] == 4096
    
    # Test float override
    os.environ["VM_DISK_SIZE"] = "30.5"
    _apply_env_overrides(config)
    assert config["vm"]["disk_size"] == 30.5
    
    # Test boolean override
    os.environ["VM_ENABLED"] = "true"
    config["vm"]["enabled"] = False
    _apply_env_overrides(config)
    assert config["vm"]["enabled"] is True
    
    # Test string override
    os.environ["VM_NAME"] = "test-vm"
    config["vm"]["name"] = "default"
    _apply_env_overrides(config)
    assert config["vm"]["name"] == "test-vm"
    
    # Test invalid type conversion
    os.environ["VM_MEMORY"] = "invalid"
    _apply_env_overrides(config)
    assert config["vm"]["memory"] == 4096  # Should keep previous value

def test_missing_config_values():
    """Test handling of missing configuration values"""
    with patch('json.load', return_value={}):
        config = load_config()
        assert isinstance(config, dict)
        assert not config  # Should be empty but not raise an error 