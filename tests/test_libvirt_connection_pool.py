import pytest
import asyncio
import libvirt
from unittest.mock import patch, MagicMock
from kvm_mcp_server import LibvirtConnectionPool

@pytest.mark.asyncio
async def test_connection_pool_initialization():
    """Test the initialization of the connection pool"""
    with patch('libvirt.open') as mock_open:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        
        pool = LibvirtConnectionPool(max_connections=2)
        assert pool.active_connections == 2
        assert pool.connections.qsize() == 2
        assert mock_open.call_count == 2

@pytest.mark.asyncio
async def test_connection_pool_get_connection():
    """Test getting a connection from the pool"""
    with patch('libvirt.open') as mock_open:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        
        pool = LibvirtConnectionPool(max_connections=1)
        async with pool.get_connection() as conn:
            assert conn == mock_conn
            assert pool.active_connections == 1

@pytest.mark.asyncio
async def test_connection_pool_timeout():
    """Test connection pool timeout behavior"""
    with patch('libvirt.open') as mock_open:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        
        pool = LibvirtConnectionPool(max_connections=1, timeout=0.1)
        # Get first connection
        async with pool.get_connection():
            # Try to get another connection (should timeout and create new one)
            async with pool.get_connection() as conn:
                assert conn == mock_conn
                assert mock_open.call_count == 2

@pytest.mark.asyncio
async def test_connection_pool_dead_connection():
    """Test handling of dead connections"""
    with patch('libvirt.open') as mock_open:
        mock_conn = MagicMock()
        mock_conn.getVersion.side_effect = libvirt.libvirtError("Connection dead")
        mock_open.return_value = mock_conn
        
        pool = LibvirtConnectionPool(max_connections=1)
        async with pool.get_connection():
            pass  # Connection will be detected as dead and replaced
        
        assert pool.active_connections == 1
        assert mock_open.call_count == 2

@pytest.mark.asyncio
async def test_connection_pool_close_all():
    """Test closing all connections in the pool"""
    with patch('libvirt.open') as mock_open:
        mock_conn = MagicMock()
        mock_open.return_value = mock_conn
        
        pool = LibvirtConnectionPool(max_connections=2)
        await pool.close_all()
        assert pool.active_connections == 0
        assert pool.connections.empty()

@pytest.mark.asyncio
async def test_connection_pool_error_handling():
    """Test error handling during initialization and connection retrieval"""
    with patch('libvirt.open') as mock_open:
        mock_open.side_effect = libvirt.libvirtError("Connection failed")
        
        # Test initialization with errors
        pool = LibvirtConnectionPool(max_connections=2)
        assert pool.active_connections == 0
        
        # Test connection retrieval with errors
        with pytest.raises(libvirt.libvirtError):
            async with pool.get_connection():
                pass 