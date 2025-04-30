import pytest
from unittest.mock import patch, MagicMock
from kvm_mcp_server import handle_request
import json

@pytest.mark.asyncio
async def test_initialize_request(mock_libvirt_conn):
    """Test initialization request handling"""
    with patch('libvirt.open') as mock_open:
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
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "1.0"
        assert response["result"]["serverInfo"]["name"] == "kvm-control"

@pytest.mark.asyncio
async def test_list_vms_request():
    """Test list_vms request handling"""
    # Mock list_vms function
    mock_vms = [{"name": "test-vm", "state": "running"}]
    
    with patch('kvm_mcp_server.list_vms', return_value=mock_vms):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_vms",
                "arguments": {}
            },
            "id": 2
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert response["result"] == mock_vms

@pytest.mark.asyncio
async def test_create_vm_request():
    """Test create_vm request handling"""
    # Mock create_vm function
    mock_result = {"status": "success", "message": "VM created"}
    
    with patch('kvm_mcp_server.create_vm', return_value=mock_result):
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
            "id": 3
        }
        
        response = await handle_request(json.dumps(request))
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert response["result"] == mock_result

@pytest.mark.asyncio
async def test_invalid_method():
    """Test handling of invalid method"""
    request = {
        "jsonrpc": "2.0",
        "method": "invalid_method",
        "params": {},
        "id": 4
    }
    
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]

@pytest.mark.asyncio
async def test_missing_method():
    """Test handling of missing method"""
    request = {
        "jsonrpc": "2.0",
        "params": {},
        "id": 5
    }
    
    response = await handle_request(json.dumps(request))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]

@pytest.mark.asyncio
async def test_invalid_json():
    """Test handling of invalid JSON"""
    response = await handle_request("invalid json")
    assert response["jsonrpc"] == "2.0"
    assert response["error"]["code"] == -32700
    assert "Parse error" in response["error"]["message"]
    assert response["id"] is None
 