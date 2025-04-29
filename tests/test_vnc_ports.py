import pytest
from unittest.mock import patch, MagicMock
from kvm_mcp_server import get_vnc_ports

@pytest.mark.asyncio
async def test_get_vnc_ports_success():
    """Test successful retrieval of VNC ports"""
    # Mock data
    running_vms = "test-vm1\ntest-vm2\n"
    vnc_displays = {
        "test-vm1": ":1\n",  # Should map to port 5901
        "test-vm2": ":2\n"   # Should map to port 5902
    }

    # Create mock subprocess run function
    def mock_subprocess_run(args, **kwargs):
        mock_result = MagicMock()
        if args[0] == 'virsh' and args[1] == 'list':
            mock_result.returncode = 0
            mock_result.stdout = running_vms
        elif args[0] == 'virsh' and args[1] == 'vncdisplay':
            vm_name = args[2]
            mock_result.returncode = 0
            mock_result.stdout = vnc_displays.get(vm_name, '')
        return mock_result

    # Patch subprocess.run
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        result = await get_vnc_ports("get_vnc_ports", {})
        
        assert result["status"] == "success"
        assert "vnc_ports" in result
        assert result["vnc_ports"]["test-vm1"] == 5901
        assert result["vnc_ports"]["test-vm2"] == 5902

@pytest.mark.asyncio
async def test_get_vnc_ports_no_vms():
    """Test VNC port retrieval when no VMs are running"""
    def mock_subprocess_run(args, **kwargs):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\n"  # Empty list of VMs
        return mock_result

    with patch('subprocess.run', side_effect=mock_subprocess_run):
        result = await get_vnc_ports("get_vnc_ports", {})
        
        assert result["status"] == "success"
        assert "vnc_ports" in result
        assert len(result["vnc_ports"]) == 0

@pytest.mark.asyncio
async def test_get_vnc_ports_virsh_error():
    """Test error handling when virsh command fails"""
    def mock_subprocess_run(args, **kwargs):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Failed to connect to hypervisor"
        return mock_result

    with patch('subprocess.run', side_effect=mock_subprocess_run):
        result = await get_vnc_ports("get_vnc_ports", {})
        
        assert result["status"] == "error"
        assert "Failed to get VM list" in result["message"]

@pytest.mark.asyncio
async def test_get_vnc_ports_invalid_display():
    """Test handling of invalid VNC display numbers"""
    # Mock data with an invalid display number
    running_vms = "test-vm1\ntest-vm2\n"
    vnc_displays = {
        "test-vm1": ":1\n",      # Valid display
        "test-vm2": "invalid\n"  # Invalid display
    }

    def mock_subprocess_run(args, **kwargs):
        mock_result = MagicMock()
        if args[0] == 'virsh' and args[1] == 'list':
            mock_result.returncode = 0
            mock_result.stdout = running_vms
        elif args[0] == 'virsh' and args[1] == 'vncdisplay':
            vm_name = args[2]
            mock_result.returncode = 0
            mock_result.stdout = vnc_displays.get(vm_name, '')
        return mock_result

    with patch('subprocess.run', side_effect=mock_subprocess_run):
        result = await get_vnc_ports("get_vnc_ports", {})
        
        assert result["status"] == "success"
        assert "vnc_ports" in result
        assert result["vnc_ports"]["test-vm1"] == 5901
        assert "test-vm2" not in result["vnc_ports"]  # Invalid display should be skipped 