import pytest
import os
from pathlib import Path

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