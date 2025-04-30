import pytest
from unittest.mock import patch, MagicMock, Mock
import libvirt
from kvm_mcp_server import handle_request, create_vm, start_vm, stop_vm, reboot_vm, get_vnc_ports, get_vm_ip, list_vms
import json
import subprocess

@pytest.fixture
def mock_conn():
    """Fixture to provide a mock libvirt connection"""
    conn = MagicMock()
    return conn

@pytest.fixture
def mock_domain():
    """Fixture to provide a mock libvirt domain"""
    domain = MagicMock()
    return domain

@pytest.mark.asyncio
async def test_create_vm_libvirt_error():
    """Test handling of libvirt errors during VM creation"""
    with patch('libvirt.open') as mock_open, \
         patch('subprocess.run') as mock_run:
        # Mock subprocess.run to succeed
        mock_run.return_value = MagicMock(returncode=0)
        
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        # Mock lookupByName to raise domain not found error
        mock_conn.lookupByName.side_effect = libvirt.libvirtError("domain not found")
        # Then mock defineXML to raise the error we want to test
        mock_conn.defineXML.side_effect = libvirt.libvirtError("Failed to define VM")
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "create_vm",
                "arguments": {
                    "name": "test-vm",
                    "memory": 2048,
                    "vcpus": 2,
                    "disk_size": 20
                }
            },
            "id": 1
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "Failed to define VM" in response["error"]["message"]

@pytest.mark.asyncio
async def test_start_vm_libvirt_error(mock_libvirt_conn):
    """Test handling of libvirt errors during VM start"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError("VM not found")
        mock_open.return_value = mock_libvirt_conn
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "start_vm",
                "arguments": {
                    "name": "test-vm"
                }
            },
            "id": 1
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "VM not found" in response["error"]["message"]

@pytest.mark.asyncio
async def test_stop_vm_libvirt_error(mock_libvirt_conn):
    """Test handling of libvirt errors during VM stop"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError("VM not found")
        mock_open.return_value = mock_libvirt_conn
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "stop_vm",
                "arguments": {
                    "name": "test-vm"
                }
            },
            "id": 1
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "VM not found" in response["error"]["message"]

@pytest.mark.asyncio
async def test_reboot_vm_libvirt_error(mock_libvirt_conn):
    """Test handling of libvirt errors during VM reboot"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError("VM not found")
        mock_open.return_value = mock_libvirt_conn
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "reboot_vm",
                "arguments": {
                    "name": "test-vm"
                }
            },
            "id": 1
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "VM not found" in response["error"]["message"]

@pytest.mark.asyncio
async def test_get_vnc_ports_error():
    """Test handling of errors during VNC port retrieval"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Failed to run virsh command")
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_vnc_ports",
                "arguments": {}
            },
            "id": 1
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "Failed to run virsh command" in response["error"]["message"]

@pytest.mark.asyncio
async def test_get_vm_ip_error():
    """Test handling of errors during VM IP retrieval"""
    with patch('libvirt.open') as mock_open:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        mock_domain = MagicMock()
        mock_conn.lookupByName.return_value = mock_domain
        mock_domain.interfaceAddresses.side_effect = libvirt.libvirtError("Failed to get interface addresses")
        
        ip = get_vm_ip(mock_domain)
        assert ip is None

@pytest.mark.asyncio
async def test_handle_request_invalid_params():
    """Test handling of invalid parameters in JSON-RPC requests"""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": "invalid",  # params should be a dict
        "id": 1
    }
    
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert "error" in response
    assert response["error"]["code"] == -32602
    assert "Invalid params" in response["error"]["message"]

@pytest.mark.asyncio
async def test_handle_request_internal_error():
    """Test handling of internal errors in JSON-RPC requests"""
    with patch('kvm_mcp_server.create_vm', side_effect=Exception("Internal error")):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "create_vm",
                "arguments": {
                    "name": "test-vm",
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
        assert "Internal error" in response["error"]["message"]

@pytest.mark.asyncio
async def test_handle_initialize_error(mock_libvirt_conn):
    """Test handling of errors during initialization"""
    with patch('libvirt.open') as mock_open, \
         patch('kvm_mcp_server.handle_initialize', side_effect=Exception("Initialization failed")):
        mock_open.return_value = mock_libvirt_conn
        
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client"}
            },
            "id": 1
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "Initialization failed" in response["error"]["message"]

@pytest.mark.asyncio
async def test_list_vms_domain_error(mock_libvirt_conn, mock_libvirt_domain):
    """Test VM listing with domain error"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.listAllDomains.return_value = [mock_libvirt_domain]
        mock_libvirt_domain.state.return_value = (1, 0)  # Mock state and reason
        mock_libvirt_domain.name.side_effect = libvirt.libvirtError("Domain error")
        mock_open.return_value = mock_libvirt_conn
        
        result = await list_vms("list_vms", {})
        
        assert len(result) == 1
        assert "error" in result[0]
        assert "Domain error" in result[0]["error"]

@pytest.mark.asyncio
async def test_start_vm_domain_error(mock_libvirt_conn):
    """Test handling of domain errors during VM start"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
        mock_open.return_value = mock_libvirt_conn
        
        result = await start_vm("start_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

@pytest.mark.asyncio
async def test_start_vm_create_error(mock_libvirt_conn, mock_libvirt_domain):
    """Test handling of create errors during VM start"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.return_value = mock_libvirt_domain
        mock_libvirt_domain.create.return_value = -1  # Simulate create failure
        mock_open.return_value = mock_libvirt_conn
        
        result = await start_vm("start_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "failed to start" in result["message"].lower()

@pytest.mark.asyncio
async def test_stop_vm_domain_error(mock_libvirt_conn):
    """Test handling of domain errors during VM stop"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
        mock_open.return_value = mock_libvirt_conn
        
        result = await stop_vm("stop_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

@pytest.mark.asyncio
async def test_stop_vm_shutdown_error(mock_libvirt_conn, mock_libvirt_domain):
    """Test handling of shutdown errors during VM stop"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.return_value = mock_libvirt_domain
        mock_libvirt_domain.shutdown.return_value = -1  # Simulate shutdown failure
        mock_open.return_value = mock_libvirt_conn
        
        result = await stop_vm("stop_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "failed to stop" in result["message"].lower()

@pytest.mark.asyncio
async def test_reboot_vm_domain_error(mock_libvirt_conn):
    """Test handling of domain errors during VM reboot"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
        mock_open.return_value = mock_libvirt_conn
        
        result = await reboot_vm("reboot_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

@pytest.mark.asyncio
async def test_reboot_vm_reboot_error(mock_libvirt_conn, mock_libvirt_domain):
    """Test handling of reboot errors during VM reboot"""
    with patch('libvirt.open') as mock_open:
        mock_libvirt_conn.lookupByName.return_value = mock_libvirt_domain
        mock_libvirt_domain.reboot.return_value = -1  # Simulate reboot failure
        mock_open.return_value = mock_libvirt_conn
        
        result = await reboot_vm("reboot_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "failed to reboot" in result["message"].lower()

@pytest.mark.asyncio
@patch('subprocess.run')
@patch('libvirt.open')
async def test_get_vnc_ports_virsh_error(mock_libvirt_open, mock_run, mock_conn):
    """Test VNC port retrieval with virsh error"""
    mock_libvirt_open.return_value = mock_conn
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Virsh error"
    )
    
    result = await get_vnc_ports("get_vnc_ports", {})
    
    assert result["status"] == "error"
    assert "Failed to get VM list" in result["message"]
    assert "Virsh error" in result["error"]

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_create_vm_invalid_name(mock_libvirt_open):
    """Test VM creation with invalid name"""
    result = await create_vm("create_vm", {"name": "invalid@name"})
    
    assert result["status"] == "error"
    assert "VM name contains invalid characters" in result["message"]
    mock_libvirt_open.assert_not_called()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_create_vm_invalid_memory(mock_libvirt_open):
    """Test VM creation with invalid memory"""
    result = await create_vm("create_vm", {
        "name": "test-vm",
        "memory": 100,  # Less than minimum 256MB
        "vcpus": 2,
        "disk_size": 20
    })
    
    assert result["status"] == "error"
    assert "Memory must be at least 256MB" in result["message"]
    mock_libvirt_open.assert_not_called()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_create_vm_invalid_vcpus(mock_libvirt_open):
    """Test VM creation with invalid vCPUs"""
    result = await create_vm("create_vm", {
        "name": "test-vm",
        "memory": 1024,
        "vcpus": 0,  # Less than minimum 1
        "disk_size": 20
    })
    
    assert result["status"] == "error"
    assert "Must have at least 1 vCPU" in result["message"]
    mock_libvirt_open.assert_not_called()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_create_vm_invalid_disk_size(mock_libvirt_open):
    """Test VM creation with invalid disk size"""
    result = await create_vm("create_vm", {
        "name": "test-vm",
        "memory": 1024,
        "vcpus": 2,
        "disk_size": 0  # Less than minimum 1GB
    })
    
    assert result["status"] == "error"
    assert "Disk size must be at least 1GB" in result["message"]
    mock_libvirt_open.assert_not_called()

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_create_vm_connection_error(mock_libvirt_open):
    """Test VM creation with connection error"""
    mock_libvirt_open.return_value = None
    
    result = await create_vm("create_vm", {
        "name": "test-vm",
        "memory": 1024,
        "vcpus": 2,
        "disk_size": 20
    })
    
    assert result["status"] == "error"
    assert "Failed to connect to libvirt daemon" in result["message"]

@pytest.mark.asyncio
@patch('libvirt.open')
async def test_create_vm_already_exists(mock_libvirt_open, mock_conn):
    """Test VM creation when VM already exists"""
    mock_libvirt_open.return_value = mock_conn
    mock_conn.lookupByName.return_value = Mock()  # Simulate existing VM
    
    result = await create_vm("create_vm", {
        "name": "test-vm",
        "memory": 1024,
        "vcpus": 2,
        "disk_size": 20
    })
    
    assert result["status"] == "error"
    assert "VM test-vm already exists" in result["message"] 