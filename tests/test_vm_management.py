import pytest
import libvirt
from unittest.mock import Mock, patch
from kvm_mcp_server import list_vms, start_vm, stop_vm, reboot_vm, get_vnc_ports

@pytest.fixture
def mock_domain():
    domain = Mock()
    domain.name.return_value = "test-vm"
    domain.ID.return_value = 1
    domain.state.return_value = (libvirt.VIR_DOMAIN_RUNNING, 0)
    domain.maxMemory.return_value = 2048 * 1024  # 2GB in KB
    domain.maxVcpus.return_value = 2
    return domain

@pytest.fixture
def mock_conn(mock_domain):
    conn = Mock()
    conn.listAllDomains.return_value = [mock_domain]
    conn.lookupByName.return_value = mock_domain
    return conn

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_list_vms_success(mock_libvirt_open, mock_conn):
    """Test successful listing of VMs"""
    mock_libvirt_open.return_value = mock_conn
    
    result = await list_vms("list_vms", {})
    
    assert len(result) == 1
    vm = result[0]
    assert vm["name"] == "test-vm"
    assert vm["id"] == 1
    assert vm["state"] == "running"
    assert vm["memory"] == 2048  # MB
    assert vm["vcpu"] == 2

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_list_vms_connection_error(mock_libvirt_open):
    """Test VM listing with connection error"""
    mock_libvirt_open.return_value = None
    
    result = await list_vms("list_vms", {})
    
    assert len(result) == 1
    assert "error" in result[0]
    assert "Failed to connect to libvirt daemon" in result[0]["error"]

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_list_vms_libvirt_error(mock_libvirt_open):
    """Test VM listing with libvirt error"""
    mock_libvirt_open.side_effect = libvirt.libvirtError("Test error")
    
    result = await list_vms("list_vms", {})
    
    assert len(result) == 1
    assert "error" in result[0]
    assert "Test error" in result[0]["error"]

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_start_vm_success(mock_libvirt_open, mock_conn, mock_domain):
    """Test successful VM start"""
    mock_libvirt_open.return_value = mock_conn
    mock_domain.create.return_value = 0
    
    result = await start_vm("start_vm", {"name": "test-vm"})
    
    assert result["status"] == "success"
    assert "started successfully" in result["message"]
    mock_domain.create.assert_called_once()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_start_vm_missing_name(mock_libvirt_open):
    """Test VM start with missing name"""
    result = await start_vm("start_vm", {})
    
    assert result["status"] == "error"
    assert "VM name not provided" in result["message"]
    mock_libvirt_open.assert_not_called()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_start_vm_connection_error(mock_libvirt_open):
    """Test VM start with connection error"""
    mock_libvirt_open.return_value = None
    
    result = await start_vm("start_vm", {"name": "test-vm"})
    
    assert result["status"] == "error"
    assert "Failed to connect to libvirt daemon" in result["message"]

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_stop_vm_success(mock_libvirt_open, mock_conn, mock_domain):
    """Test successful VM stop"""
    mock_libvirt_open.return_value = mock_conn
    mock_domain.shutdown.return_value = 0
    
    result = await stop_vm("stop_vm", {"name": "test-vm"})
    
    assert result["status"] == "success"
    assert "stopped successfully" in result["message"]
    mock_domain.shutdown.assert_called_once()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_stop_vm_missing_name(mock_libvirt_open):
    """Test VM stop with missing name"""
    result = await stop_vm("stop_vm", {})
    
    assert result["status"] == "error"
    assert "VM name not provided" in result["message"]
    mock_libvirt_open.assert_not_called()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_stop_vm_connection_error(mock_libvirt_open):
    """Test VM stop with connection error"""
    mock_libvirt_open.return_value = None
    
    result = await stop_vm("stop_vm", {"name": "test-vm"})
    
    assert result["status"] == "error"
    assert "Failed to connect to libvirt daemon" in result["message"]

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_reboot_vm_success(mock_libvirt_open, mock_conn, mock_domain):
    """Test successful VM reboot"""
    mock_libvirt_open.return_value = mock_conn
    mock_domain.reboot.return_value = 0
    
    result = await reboot_vm("reboot_vm", {"name": "test-vm"})
    
    assert result["status"] == "success"
    assert "rebooted successfully" in result["message"]
    mock_domain.reboot.assert_called_once()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_reboot_vm_missing_name(mock_libvirt_open):
    """Test VM reboot with missing name"""
    result = await reboot_vm("reboot_vm", {})
    
    assert result["status"] == "error"
    assert "VM name not provided" in result["message"]
    mock_libvirt_open.assert_not_called()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_reboot_vm_connection_error(mock_libvirt_open):
    """Test VM reboot with connection error"""
    mock_libvirt_open.return_value = None
    
    result = await reboot_vm("reboot_vm", {"name": "test-vm"})
    
    assert result["status"] == "error"
    assert "Failed to connect to libvirt daemon" in result["message"]

@pytest.mark.asyncio
@patch('subprocess.check_output')
@patch('libvirt.open')
async def test_get_vnc_ports_success(mock_libvirt_open, mock_check_output, mock_conn, mock_domain):
    """Test successful VNC port retrieval"""
    mock_libvirt_open.return_value = mock_conn
    mock_check_output.return_value = b"Id Name                 State\n----------------------------------\n 1  test-vm              running\n"
    
    result = await get_vnc_ports("get_vnc_ports", {})
    
    assert result["status"] == "success"
    assert "vnc_ports" in result
    assert isinstance(result["vnc_ports"], dict)

@pytest.mark.asyncio
@patch('subprocess.check_output')
@patch('libvirt.open')
async def test_get_vnc_ports_no_vms(mock_libvirt_open, mock_check_output, mock_conn):
    """Test VNC port retrieval with no running VMs"""
    mock_libvirt_open.return_value = mock_conn
    mock_check_output.return_value = b"Id Name                 State\n----------------------------------\n"
    
    result = await get_vnc_ports("get_vnc_ports", {})
    
    assert result["status"] == "success"
    assert "vnc_ports" in result
    assert result["vnc_ports"] == {} 