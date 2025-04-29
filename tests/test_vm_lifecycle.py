import pytest
from unittest.mock import patch, MagicMock
from kvm_mcp_server import create_vm, start_vm, stop_vm, reboot_vm

@pytest.mark.asyncio
async def test_create_vm_success():
    """Test successful VM creation"""
    # Mock libvirt connection and domain
    mock_conn = MagicMock()
    mock_domain = MagicMock()
    mock_conn.lookupByName.return_value = None
    mock_conn.defineXML.return_value = mock_domain
    mock_domain.create.return_value = 0

    with patch('libvirt.open', return_value=mock_conn), \
         patch('subprocess.run', return_value=MagicMock(returncode=0)):
        result = await create_vm("create_vm", {
            "name": "test-vm",
            "memory": 2048,
            "vcpus": 2,
            "disk_size": 20,
            "master_image": "/path/to/image.qcow2"
        })
        
        assert result["status"] == "success"
        assert "test-vm" in result["message"]

@pytest.mark.asyncio
async def test_create_vm_already_exists():
    """Test VM creation when VM already exists"""
    # Mock libvirt connection and domain
    mock_conn = MagicMock()
    mock_domain = MagicMock()
    mock_conn.lookupByName.return_value = mock_domain

    with patch('libvirt.open', return_value=mock_conn):
        result = await create_vm("create_vm", {
            "name": "test-vm",
            "memory": 2048,
            "vcpus": 2
        })
        
        assert result["status"] == "error"
        assert "already exists" in result["message"]

@pytest.mark.asyncio
async def test_start_vm_success():
    """Test successful VM start"""
    # Mock libvirt connection and domain
    mock_conn = MagicMock()
    mock_domain = MagicMock()
    mock_conn.lookupByName.return_value = mock_domain
    mock_domain.create.return_value = 0

    with patch('libvirt.open', return_value=mock_conn):
        result = await start_vm("start_vm", {"name": "test-vm"})
        
        assert result["status"] == "success"
        assert "started successfully" in result["message"]

@pytest.mark.asyncio
async def test_stop_vm_success():
    """Test successful VM stop"""
    # Mock libvirt connection and domain
    mock_conn = MagicMock()
    mock_domain = MagicMock()
    mock_conn.lookupByName.return_value = mock_domain
    mock_domain.shutdown.return_value = 0

    with patch('libvirt.open', return_value=mock_conn):
        result = await stop_vm("stop_vm", {"name": "test-vm"})
        
        assert result["status"] == "success"
        assert "stopped successfully" in result["message"]

@pytest.mark.asyncio
async def test_reboot_vm_success():
    """Test successful VM reboot"""
    # Mock libvirt connection and domain
    mock_conn = MagicMock()
    mock_domain = MagicMock()
    mock_conn.lookupByName.return_value = mock_domain
    mock_domain.reboot.return_value = 0

    with patch('libvirt.open', return_value=mock_conn):
        result = await reboot_vm("reboot_vm", {"name": "test-vm"})
        
        assert result["status"] == "success"
        assert "rebooted successfully" in result["message"]

@pytest.mark.asyncio
async def test_vm_operations_invalid_name():
    """Test VM operations with invalid name"""
    for operation in [start_vm, stop_vm, reboot_vm]:
        result = await operation("operation", {})
        assert result["status"] == "error"
        assert "name not provided" in result["message"]

@pytest.mark.asyncio
async def test_vm_operations_connection_error():
    """Test VM operations with connection error"""
    with patch('libvirt.open', return_value=None):
        for operation in [start_vm, stop_vm, reboot_vm]:
            result = await operation("operation", {"name": "test-vm"})
            assert result["status"] == "error"
            assert "Failed to connect" in result["message"] 