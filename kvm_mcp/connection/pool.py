import libvirt
import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger('kvm_mcp')

class LibvirtConnectionPool:
    """A simple connection pool for libvirt to avoid repeated connections."""
    
    def __init__(self, uri='qemu:///system', max_connections=5, timeout=30):
        self.uri = uri
        self.max_connections = max_connections
        self.timeout = timeout
        self.connections = asyncio.Queue(maxsize=max_connections)
        self.active_connections = 0
        self._initialize()
    
    def _initialize(self):
        """Initialize the connection pool with connections."""
        for _ in range(self.max_connections):
            try:
                conn = libvirt.open(self.uri)
                if conn:
                    self.connections.put_nowait(conn)
                    self.active_connections += 1
                    logger.debug(f"Added connection to pool, active: {self.active_connections}")
            except libvirt.libvirtError as e:
                logger.error(f"Failed to initialize libvirt connection: {str(e)}")
                # Don't raise - allow partial pool initialization
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            # Try to get from the pool first
            try:
                conn = await asyncio.wait_for(self.connections.get(), self.timeout)
                logger.debug("Got connection from pool")
                yield conn
            except asyncio.TimeoutError:
                # If the pool is empty and we reach max, create a new one
                logger.warning("Connection pool timeout, creating new connection")
                conn = libvirt.open(self.uri)
                if not conn:
                    raise libvirt.libvirtError("Failed to connect to libvirt daemon")
                yield conn
        except libvirt.libvirtError as e:
            logger.error(f"Libvirt connection error: {str(e)}")
            raise
        finally:
            # Return the connection to the pool if it's still valid
            if conn:
                try:
                    # Simple check if connection is alive
                    conn.getVersion()
                    await self.connections.put(conn)
                    logger.debug("Returned connection to pool")
                except libvirt.libvirtError:
                    # Connection is dead, close it
                    try:
                        conn.close()
                        self.active_connections -= 1
                        logger.warning(f"Closed dead connection, active: {self.active_connections}")
                    except:
                        pass
                    
                    # Create a new one if possible
                    try:
                        new_conn = libvirt.open(self.uri)
                        if new_conn:
                            await self.connections.put(new_conn)
                            self.active_connections += 1
                            logger.debug(f"Created replacement connection, active: {self.active_connections}")
                    except:
                        logger.error("Failed to create replacement connection")

    async def close_all(self):
        """Close all connections in the pool."""
        while not self.connections.empty():
            try:
                conn = self.connections.get_nowait()
                conn.close()
                self.active_connections -= 1
                logger.debug(f"Closed connection, active: {self.active_connections}")
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")

# Create a global connection pool instance
connection_pool = LibvirtConnectionPool() 