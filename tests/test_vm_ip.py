import pytest
from unittest.mock import patch, MagicMock
from kvm_mcp_server import get_vm_ip

def test_get_vm_ip_success():
    """Test successful IP address retrieval"""
    # Mock domain with IP address
    mock_domain = MagicMock()
    mock_domain.interfaceAddresses.return_value = {
        'eth0': {
            'addrs': [
                {
                    'type': 0,  # VIR_IP_ADDR_TYPE_IPV4
                    'addr': '192.168.1.100'
                }
            ]
        }
    }

    ip = get_vm_ip(mock_domain)
    assert ip == '192.168.1.100'

def test_get_vm_ip_no_addresses():
    """Test IP retrieval when no addresses are available"""
    # Mock domain with no IP addresses
    mock_domain = MagicMock()
    mock_domain.interfaceAddresses.return_value = {
        'eth0': {
            'addrs': []
        }
    }

    ip = get_vm_ip(mock_domain)
    assert ip is None

def test_get_vm_ip_multiple_interfaces():
    """Test IP retrieval with multiple network interfaces"""
    # Mock domain with multiple interfaces
    mock_domain = MagicMock()
    mock_domain.interfaceAddresses.return_value = {
        'eth0': {
            'addrs': [
                {
                    'type': 0,  # VIR_IP_ADDR_TYPE_IPV4
                    'addr': '192.168.1.100'
                }
            ]
        },
        'eth1': {
            'addrs': [
                {
                    'type': 0,  # VIR_IP_ADDR_TYPE_IPV4
                    'addr': '10.0.0.100'
                }
            ]
        }
    }

    ip = get_vm_ip(mock_domain)
    # Should return the first IPv4 address found
    assert ip == '192.168.1.100'

def test_get_vm_ip_ipv6_only():
    """Test IP retrieval when only IPv6 addresses are available"""
    # Mock domain with only IPv6 addresses
    mock_domain = MagicMock()
    mock_domain.interfaceAddresses.return_value = {
        'eth0': {
            'addrs': [
                {
                    'type': 1,  # VIR_IP_ADDR_TYPE_IPV6
                    'addr': '2001:db8::1'
                }
            ]
        }
    }

    ip = get_vm_ip(mock_domain)
    assert ip is None

def test_get_vm_ip_exception_handling():
    """Test IP retrieval when an exception occurs"""
    # Mock domain that raises an exception
    mock_domain = MagicMock()
    mock_domain.interfaceAddresses.side_effect = Exception("Test error")

    ip = get_vm_ip(mock_domain)
    assert ip is None 