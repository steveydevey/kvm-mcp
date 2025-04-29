import pytest
from kvm_mcp_server import server, load_config, list_vms, start_vm, stop_vm, reboot_vm

@pytest.mark.asyncio
async def test_server_initialization(test_config):
    """Test that the server is initialized with valid configuration"""
    assert server is not None
    assert server.name == "kvm-control"

    # Test config loading
    config = load_config()
    assert isinstance(config, dict)
    assert "vm" in config

@pytest.mark.asyncio
async def test_list_vms(test_config):
    """Test listing VMs functionality"""
    result = await list_vms("list_vms", {})
    assert isinstance(result, list)
    # Even if no VMs are running, it should return an empty list or error dict
    assert result == [] or isinstance(result[0], dict)

@pytest.mark.asyncio
async def test_vm_operations_validation(test_config):
    """Test VM operations input validation"""
    # Test start_vm with missing name
    result = await start_vm("start_vm", {})
    assert result["status"] == "error"
    assert "VM name not provided" in result["message"]

    # Test stop_vm with missing name
    result = await stop_vm("stop_vm", {})
    assert result["status"] == "error"
    assert "VM name not provided" in result["message"]

    # Test reboot_vm with missing name
    result = await reboot_vm("reboot_vm", {})
    assert result["status"] == "error"
    assert "VM name not provided" in result["message"] 