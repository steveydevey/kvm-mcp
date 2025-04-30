import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock
import libvirt

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Add project root to Python path
project_root = Path(__file__).parent.parent
os.environ["PYTHONPATH"] = str(project_root)

@pytest.fixture(scope="session")
def test_config():
    """Fixture to provide test configuration"""
    return {
        "test_vm_name": "test-vm",
        "test_vm_memory": 1024,  # MB
        "test_vm_cpus": 1,
    }

@pytest.fixture
def mock_libvirt_conn():
    """Fixture to provide a mock libvirt connection with proper network handling"""
    conn = MagicMock()
    # Mock network lookup to handle brforvms bridge
    mock_network = MagicMock()
    mock_network.isActive.return_value = True
    conn.networkLookupByName.return_value = mock_network
    return conn

@pytest.fixture
def mock_libvirt_domain():
    """Fixture to provide a mock libvirt domain"""
    domain = MagicMock()
    domain.state.return_value = (libvirt.VIR_DOMAIN_RUNNING, 0)
    return domain 