import pytest
from unittest.mock import patch, MagicMock
import libvirt
from kvm_mcp_server import start_vm, stop_vm, reboot_vm, list_vms, get_vnc_ports
import asyncio

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
async def test_start_vm_already_running(mock_conn, mock_domain):
    """Test starting a VM that is already running"""
    with patch('libvirt.open') as mock_libvirt_open:
        mock_libvirt_open.return_value = mock_conn
        mock_conn.lookupByName.return_value = mock_domain
        mock_domain.state.return_value = (libvirt.VIR_DOMAIN_RUNNING, 0)
        
        result = await start_vm("start_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "VM test-vm is already running" in result["message"]

@pytest.mark.asyncio
async def test_stop_vm_already_stopped(mock_conn, mock_domain):
    """Test stopping a VM that is already stopped"""
    with patch('libvirt.open') as mock_libvirt_open:
        mock_libvirt_open.return_value = mock_conn
        mock_conn.lookupByName.return_value = mock_domain
        mock_domain.state.return_value = (libvirt.VIR_DOMAIN_SHUTOFF, 0)
        
        result = await stop_vm("stop_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "VM test-vm is already stopped" in result["message"]

@pytest.mark.asyncio
async def test_reboot_vm_when_stopped(mock_conn, mock_domain):
    """Test rebooting a VM that is stopped"""
    with patch('libvirt.open') as mock_libvirt_open:
        mock_libvirt_open.return_value = mock_conn
        mock_conn.lookupByName.return_value = mock_domain
        mock_domain.state.return_value = (libvirt.VIR_DOMAIN_SHUTOFF, 0)
        
        result = await reboot_vm("reboot_vm", {"name": "test-vm"})
        assert result["status"] == "error"
        assert "Cannot reboot VM test-vm: VM is not running" in result["message"]

@pytest.mark.asyncio
async def test_vm_operations_with_empty_name():
    """Test VM operations with empty VM name"""
    operations = [start_vm, stop_vm, reboot_vm]
    for op in operations:
        result = await op(op.__name__, {"name": ""})
        assert result["status"] == "error"
        assert "VM name not provided" in result["message"]

@pytest.mark.asyncio
async def test_vm_operations_with_very_long_name(mock_conn):
    """Test VM operations with extremely long VM name"""
    very_long_name = "a" * 256  # Most filesystems have a 255 character limit
    operations = [start_vm, stop_vm, reboot_vm]
    
    with patch('libvirt.open') as mock_libvirt_open:
        mock_libvirt_open.return_value = mock_conn
        mock_conn.lookupByName.side_effect = libvirt.libvirtError("Invalid VM name")
        
        for op in operations:
            result = await op(op.__name__, {"name": very_long_name})
            assert result["status"] == "error"
            assert "Invalid VM name" in result["message"]

@pytest.mark.asyncio
async def test_list_vms_with_mixed_states(mock_conn):
    """Test listing VMs with various states including crashed and unknown states"""
    with patch('libvirt.open') as mock_libvirt_open:
        mock_libvirt_open.return_value = mock_conn
        
        # Create mock domains with different states
        domains = []
        states = [
            (libvirt.VIR_DOMAIN_RUNNING, 0),
            (libvirt.VIR_DOMAIN_SHUTOFF, 0),
            (libvirt.VIR_DOMAIN_CRASHED, 0),
            (libvirt.VIR_DOMAIN_NOSTATE, 0),
            (999, 0)  # Unknown state
        ]
        
        for i, (state, reason) in enumerate(states):
            domain = MagicMock()
            domain.name.return_value = f"vm-{i}"
            domain.state.return_value = (state, reason)
            domain.ID.return_value = i
            domain.maxMemory.return_value = 1024 * 1024  # 1GB in KB
            domain.maxVcpus.return_value = 2
            domains.append(domain)
        
        mock_conn.listAllDomains.return_value = domains
        result = await list_vms("list_vms", {})
        
        assert len(result) == len(states)
        state_map = {
            libvirt.VIR_DOMAIN_RUNNING: "running",
            libvirt.VIR_DOMAIN_SHUTOFF: "shutoff",
            libvirt.VIR_DOMAIN_CRASHED: "crashed",
            libvirt.VIR_DOMAIN_NOSTATE: "no state"
        }
        
        for i, vm in enumerate(result):
            expected_state = state_map.get(states[i][0], "unknown")
            assert vm["state"] == expected_state

@pytest.mark.asyncio
async def test_get_vnc_ports_malformed_output(mock_conn):
    """Test VNC port retrieval with malformed virsh output"""
    with patch('libvirt.open') as mock_libvirt_open, \
         patch('subprocess.run') as mock_run:
        mock_libvirt_open.return_value = mock_conn
        
        # Test cases with malformed output
        test_cases = [
            # Empty output
            {
                "list_stdout": "",
                "vncdisplay_outputs": {},
                "expected_ports": {}
            },
            # Invalid display format
            {
                "list_stdout": "test-vm\ntest-vm2\n",
                "vncdisplay_outputs": {
                    "test-vm": "abc",
                    "test-vm2": "def"
                },
                "expected_ports": {}
            },
            # Mixed valid and invalid
            {
                "list_stdout": "test-vm\ntest-vm2\ntest-vm3\n",
                "vncdisplay_outputs": {
                    "test-vm": ":1",
                    "test-vm2": "invalid",
                    "test-vm3": ":2"
                },
                "expected_ports": {
                    "test-vm": 5901,
                    "test-vm3": 5902
                }
            },
            # Display number out of reasonable range
            {
                "list_stdout": "test-vm\n",
                "vncdisplay_outputs": {
                    "test-vm": ":99999"
                },
                "expected_ports": {}
            }
        ]
        
        for case in test_cases:
            def mock_run_command(cmd, **kwargs):
                if cmd[1] == 'list':
                    return MagicMock(
                        returncode=0,
                        stdout=case["list_stdout"],
                        stderr=""
                    )
                elif cmd[1] == 'vncdisplay':
                    vm_name = cmd[2]
                    return MagicMock(
                        returncode=0,
                        stdout=case["vncdisplay_outputs"].get(vm_name, ""),
                        stderr=""
                    )
            
            mock_run.side_effect = mock_run_command
            
            result = await get_vnc_ports("get_vnc_ports", {})
            assert result["status"] == "success"
            assert result["vnc_ports"] == case["expected_ports"]

@pytest.mark.asyncio
async def test_concurrent_vm_operations(mock_conn, mock_domain):
    """Test handling multiple VM operations concurrently"""
    with patch('libvirt.open') as mock_libvirt_open:
        mock_libvirt_open.return_value = mock_conn
        mock_conn.lookupByName.return_value = mock_domain
        mock_domain.state.return_value = (libvirt.VIR_DOMAIN_RUNNING, 0)
        
        # Simulate concurrent operations
        operations = [
            start_vm("start_vm", {"name": "test-vm"}),
            stop_vm("stop_vm", {"name": "test-vm"}),
            reboot_vm("reboot_vm", {"name": "test-vm"})
        ]
        
        results = await asyncio.gather(*operations)
        
        # Verify all operations completed with appropriate status
        for result in results:
            assert "status" in result
            assert "message" in result 