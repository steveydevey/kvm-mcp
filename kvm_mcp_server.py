import libvirt
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
import asyncio
import json
import subprocess
import time
from typing import Union, Dict, Optional
from functools import wraps
from contextlib import asynccontextmanager
import signal

# Configure logging
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'kvm_mcp.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('kvm_mcp')

# Connection pool for libvirt
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

# Create a connection pool
connection_pool = LibvirtConnectionPool()

# Decorator for timing methods
def timing_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} took {elapsed:.4f} seconds")
    return wrapper

# Simple LRU cache for VM info
class VMInfoCache:
    """A simple LRU cache for VM information."""
    
    def __init__(self, max_size=50, ttl=60):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}
    
    def get(self, vm_name):
        """Get a VM's info from the cache if available and not expired."""
        if vm_name in self.cache:
            if time.time() - self.timestamps[vm_name] < self.ttl:
                return self.cache[vm_name]
            # Expired
            del self.cache[vm_name]
            del self.timestamps[vm_name]
        return None
    
    def set(self, vm_name, vm_info):
        """Set a VM's info in the cache."""
        # Remove oldest item if full
        if len(self.cache) >= self.max_size:
            oldest_vm = min(self.timestamps.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_vm]
            del self.timestamps[oldest_vm]
        
        self.cache[vm_name] = vm_info
        self.timestamps[vm_name] = time.time()
    
    def invalidate(self, vm_name=None):
        """Invalidate cache entry for a VM or the entire cache."""
        if vm_name:
            if vm_name in self.cache:
                del self.cache[vm_name]
                del self.timestamps[vm_name]
        else:
            self.cache.clear()
            self.timestamps.clear()

# Create VM info cache
vm_info_cache = VMInfoCache()

def _apply_env_overrides(config: dict, prefix: str = "") -> dict:
    """Apply environment variable overrides to configuration"""
    for key, value in config.items():
        env_key = f"{prefix}{key}".upper()
        if isinstance(value, dict):
            config[key] = _apply_env_overrides(value, f"{env_key}_")
        else:
            if env_key in os.environ:
                env_value = os.environ[env_key]
                if env_value == "":  # Handle empty strings
                    if isinstance(value, str):
                        config[key] = ""
                    continue
                try:
                    if isinstance(value, bool):
                        # For bool values, only accept specific true/false values
                        if env_value.lower() in ("true", "1", "yes", "on"):
                            config[key] = True
                        elif env_value.lower() in ("false", "0", "no", "off"):
                            config[key] = False
                        else:
                            continue  # Keep original value for invalid bool
                    elif isinstance(value, int):
                        config[key] = int(env_value)
                    elif isinstance(value, float):
                        config[key] = float(env_value)
                    else:
                        config[key] = env_value
                except (ValueError, TypeError):
                    # Keep original value if conversion fails
                    continue
    return config

# Load configuration
def load_config():
    """Load configuration from config.json and apply environment variable overrides"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in configuration file: {str(e)}", e.doc, e.pos)
    
    # Apply environment variable overrides
    _apply_env_overrides(config, prefix="")
    return config

config = load_config()

server = Server("kvm-control")

@server.call_tool()
@timing_decorator
async def list_vms(name: str, arguments: dict) -> list:
    """List all available virtual machines"""
    try:
        # Check if we should bypass cache
        use_cache = not arguments.get("no_cache", False)
        if use_cache:
            cached_list = vm_info_cache.get("_all_vms_")
            if cached_list:
                logger.debug("Returning cached VM list")
                return cached_list
        
        logger.info("Fetching VM list from libvirt")
        async with connection_pool.get_connection() as conn:
            domains = conn.listAllDomains()
            result = []
            for domain in domains:
                try:
                    state, reason = domain.state()
                    state_str = {
                        libvirt.VIR_DOMAIN_NOSTATE: "no state",
                        libvirt.VIR_DOMAIN_RUNNING: "running",
                        libvirt.VIR_DOMAIN_BLOCKED: "blocked",
                        libvirt.VIR_DOMAIN_PAUSED: "paused",
                        libvirt.VIR_DOMAIN_SHUTDOWN: "shutdown",
                        libvirt.VIR_DOMAIN_SHUTOFF: "shutoff",
                        libvirt.VIR_DOMAIN_CRASHED: "crashed",
                        libvirt.VIR_DOMAIN_PMSUSPENDED: "suspended"
                    }.get(state, "unknown")
                    
                    result.append({
                        'name': domain.name(),
                        'id': domain.ID(),
                        'state': state_str,
                        'memory': domain.maxMemory() // 1024,  # Convert to MB
                        'vcpu': domain.maxVcpus()
                    })
                except libvirt.libvirtError as e:
                    logger.warning(f"Error getting info for domain {domain.name()}: {str(e)}")
                    # If we can't get some info about a domain, still include it with what we know
                    result.append({
                        'name': domain.name(),
                        'state': 'unknown',
                        'error': str(e)
                    })
            
            # Cache the result
            if use_cache:
                vm_info_cache.set("_all_vms_", result)
            
            return result
    except libvirt.libvirtError as e:
        logger.error(f"Error listing VMs: {str(e)}")
        return [{"error": str(e)}]

@server.call_tool()
@timing_decorator
async def start_vm(name: str, arguments: dict) -> dict:
    """Start a virtual machine by name"""
    try:
        vm_name = arguments.get("name")
        if not vm_name:
            logger.error("VM name not provided")
            return {"status": "error", "message": "VM name not provided"}
        
        logger.info(f"Starting VM: {vm_name}")
        async with connection_pool.get_connection() as conn:
            domain = conn.lookupByName(vm_name)
            state, reason = domain.state()
            
            if state == libvirt.VIR_DOMAIN_RUNNING:
                logger.warning(f"VM {vm_name} is already running")
                return {"status": "error", "message": f"VM {vm_name} is already running"}
            
            if domain.create() == 0:
                # Invalidate cache for this VM and the overall VM list
                vm_info_cache.invalidate(vm_name)
                vm_info_cache.invalidate("_all_vms_")
                
                logger.info(f"VM {vm_name} started successfully")
                result = {"status": "success", "message": f"VM {vm_name} started successfully"}
            else:
                logger.error(f"Failed to start VM {vm_name}")
                result = {"status": "error", "message": f"Failed to start VM {vm_name}"}
            
            return result
    except libvirt.libvirtError as e:
        error_msg = str(e)
        logger.error(f"Error starting VM {arguments.get('name', 'unknown')}: {error_msg}")
        return {"status": "error", "message": error_msg}

@server.call_tool()
@timing_decorator
async def stop_vm(name: str, arguments: dict) -> dict:
    """Stop a virtual machine by name"""
    try:
        vm_name = arguments.get("name")
        if not vm_name:
            logger.error("VM name not provided")
            return {"status": "error", "message": "VM name not provided"}
        
        logger.info(f"Stopping VM: {vm_name}")
        async with connection_pool.get_connection() as conn:
            domain = conn.lookupByName(vm_name)
            state, reason = domain.state()
            
            if state == libvirt.VIR_DOMAIN_SHUTOFF:
                logger.warning(f"VM {vm_name} is already stopped")
                return {"status": "error", "message": f"VM {vm_name} is already stopped"}
            
            if domain.shutdown() == 0:
                # Invalidate cache for this VM and the overall VM list
                vm_info_cache.invalidate(vm_name)
                vm_info_cache.invalidate("_all_vms_")
                
                logger.info(f"VM {vm_name} stopped successfully")
                result = {"status": "success", "message": f"VM {vm_name} stopped successfully"}
            else:
                logger.error(f"Failed to stop VM {vm_name}")
                result = {"status": "error", "message": f"Failed to stop VM {vm_name}"}
            
            return result
    except libvirt.libvirtError as e:
        error_msg = str(e)
        logger.error(f"Error stopping VM {arguments.get('name', 'unknown')}: {error_msg}")
        return {"status": "error", "message": error_msg}

@server.call_tool()
async def reboot_vm(name: str, arguments: dict) -> dict:
    """Reboot a virtual machine by name"""
    try:
        vm_name = arguments.get("name")
        if not vm_name:
            return {"status": "error", "message": "VM name not provided"}
        
        conn = libvirt.open('qemu:///system')
        if conn is None:
            return {"status": "error", "message": "Failed to connect to libvirt daemon"}
        
        domain = conn.lookupByName(vm_name)
        state, reason = domain.state()
        
        if state == libvirt.VIR_DOMAIN_SHUTOFF:
            return {"status": "error", "message": f"Cannot reboot VM {vm_name}: VM is not running"}
        
        if domain.reboot() == 0:
            result = {"status": "success", "message": f"VM {vm_name} rebooted successfully"}
        else:
            result = {"status": "error", "message": f"Failed to reboot VM {vm_name}"}
        
        conn.close()
        return result
    except libvirt.libvirtError as e:
        return {"status": "error", "message": str(e)}

def generate_ignition_config(vm_name: str, arguments: dict) -> str:
    """Generate an Ignition configuration for Fedora CoreOS"""
    # Get configuration values
    hostname = arguments.get("hostname", config["vm"]["ignition"]["default_hostname"])
    user = arguments.get("user", config["vm"]["ignition"]["default_user"])
    timezone = arguments.get("timezone", config["vm"]["ignition"]["default_timezone"])
    locale = arguments.get("locale", config["vm"]["ignition"]["default_locale"])
    
    # Validate inputs
    if not hostname or not user or not timezone or not locale:
        raise ValueError("Empty values are not allowed for hostname, user, timezone, or locale")
    
    # Read SSH key
    ssh_key_path = os.path.expanduser(arguments.get("ssh_key", config["vm"]["ignition"]["default_ssh_key"]))
    if not os.path.exists(ssh_key_path):
        raise FileNotFoundError(f"SSH key not found at {ssh_key_path}")
    
    with open(ssh_key_path, 'r') as f:
        ssh_key = f.read().strip()
    
    # Generate Ignition config
    ignition_config = {
        "ignition": {
            "version": "3.3.0"
        },
        "passwd": {
            "users": [
                {
                    "name": user,
                    "sshAuthorizedKeys": [ssh_key]
                }
            ]
        },
        "storage": {
            "files": [
                {
                    "path": "/etc/hostname",
                    "mode": 420,
                    "overwrite": True,
                    "contents": {
                        "source": f"data:,{hostname}"
                    }
                },
                {
                    "path": "/etc/locale.conf",
                    "mode": 420,
                    "overwrite": True,
                    "contents": {
                        "source": f"data:,LANG={locale}"
                    }
                }
            ]
        },
        "systemd": {
            "units": [
                {
                    "name": "timezone.service",
                    "enabled": True,
                    "contents": f"""[Unit]
Description=Set timezone
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/timedatectl set-timezone {timezone}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target"""
                }
            ]
        }
    }
    
    return json.dumps(ignition_config, indent=2)

@server.call_tool()
async def create_vm(name: str, arguments: dict) -> dict:
    """Create a new VM"""
    conn = None
    try:
        # Extract parameters from arguments
        vm_name = arguments.get("name")
        memory = arguments.get("memory")
        vcpus = arguments.get("vcpus")
        disk_size = arguments.get("disk_size", 20)
        network = arguments.get("network", "brforvms")
        master_image = arguments.get("master_image")

        # Validate parameters
        if not vm_name or not isinstance(vm_name, str):
            return {"status": "error", "message": "Invalid VM name"}
        
        if any(c in "!@#$%^&*()+={}[]|\\:;\"'<>?/" for c in vm_name):
            return {"status": "error", "message": "VM name contains invalid characters"}
        
        if not isinstance(memory, int) or memory < 256:
            return {"status": "error", "message": "Memory must be at least 256MB"}
        
        if memory > 1024 * 1024:  # 1TB limit
            return {"status": "error", "message": "Memory exceeds maximum limit of 1TB"}
        
        if not isinstance(vcpus, int) or vcpus < 1:
            return {"status": "error", "message": "Must have at least 1 vCPU"}
        
        if vcpus > 128:  # 128 vCPU limit
            return {"status": "error", "message": "vCPUs exceed maximum limit of 128"}
        
        if not isinstance(disk_size, int) or disk_size < 1:
            return {"status": "error", "message": "Disk size must be at least 1GB"}
        
        if disk_size > 10000:  # 10TB limit
            return {"status": "error", "message": "Disk size exceeds maximum limit of 10TB"}
        
        if not network or not isinstance(network, str):
            return {"status": "error", "message": "Invalid network name"}

        # Create VM using libvirt
        conn = libvirt.open("qemu:///system")
        if conn is None:
            return {"status": "error", "message": "Failed to connect to libvirt daemon"}

        # Check if VM already exists
        try:
            existing_dom = conn.lookupByName(vm_name)
            if existing_dom is not None:
                return {"status": "error", "message": f"VM {vm_name} already exists"}
        except libvirt.libvirtError as e:
            if "domain not found" not in str(e).lower():
                return {"status": "error", "message": str(e)}

        # Create disk image
        disk_path = f"/vm/{vm_name}.qcow2"
        if os.path.exists(disk_path):
            return {"status": "error", "message": f"Disk image {disk_path} already exists"}

        # Create the disk image using qemu-img
        result = subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", disk_path, f"{disk_size}G"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {"status": "error", "message": f"Failed to create disk image: {result.stderr}"}

        # Create VM configuration
        xml = f"""
        <domain type='kvm'>
            <name>{vm_name}</name>
            <memory unit='MiB'>{memory}</memory>
            <vcpu>{vcpus}</vcpu>
            <os>
                <type arch='x86_64' machine='pc'>hvm</type>
                <boot dev='hd'/>
            </os>
            <devices>
                <disk type='file' device='disk'>
                    <driver name='qemu' type='qcow2'/>
                    <source file='{disk_path}'/>
                    <target dev='vda' bus='virtio'/>
                </disk>
                <interface type='bridge'>
                    <source bridge='brforvms'/>
                    <model type='virtio'/>
                </interface>
                <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'/>
            </devices>
        </domain>
        """

        # Create VM
        dom = conn.defineXML(xml)
        if dom is None:
            return {"status": "error", "message": "Failed to define VM"}

        # Start VM
        if dom.create() < 0:
            return {"status": "error", "message": "Failed to start VM"}

        return {"status": "success", "message": f"VM {vm_name} created successfully"}

    except libvirt.libvirtError as e:
        return {"status": "error", "message": f"Libvirt error: {str(e)}"}
    except subprocess.SubprocessError as e:
        return {"status": "error", "message": f"Subprocess error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
    finally:
        if conn:
            conn.close()

@server.call_tool()
async def get_vnc_ports(name: str, arguments: dict) -> dict:
    """Get VNC ports for all running VMs"""
    try:
        import subprocess
        import json
        
        # Get list of running VMs using virsh with qemu:///system connection
        result = subprocess.run(['virsh', '-c', 'qemu:///system', 'list', '--state-running', '--name'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            return {"status": "error", "message": "Failed to get VM list", "error": result.stderr}
        
        # Filter out empty lines and whitespace
        vms = [vm.strip() for vm in result.stdout.splitlines() if vm.strip()]
        vnc_ports = {}
        
        # Get VNC port for each VM
        for vm in vms:
            # Use vncdisplay command with qemu:///system connection
            port_result = subprocess.run(['virsh', '-c', 'qemu:///system', 'vncdisplay', vm], 
                                      capture_output=True, text=True)
            if port_result.returncode == 0 and port_result.stdout.strip():
                port = port_result.stdout.strip()
                # Convert display number to actual port (e.g., ":2" -> 5902)
                display_num = port.lstrip(':')
                try:
                    num = int(display_num)
                    # Validate the display number is within a reasonable range (0-99)
                    if 0 <= num <= 99:
                        vnc_ports[vm] = 5900 + num
                except ValueError:
                    # Skip invalid display numbers
                    continue
        
        return {
            "status": "success",
            "vnc_ports": vnc_ports
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_vm_ip(domain):
    """Get the IP address of a VM."""
    try:
        # Wait for the VM to get an IP address
        for _ in range(30):  # Try for 30 seconds
            ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
            if ifaces:
                for (name, val) in ifaces.items():
                    if val['addrs']:
                        for addr in val['addrs']:
                            if addr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                                return addr['addr']
            time.sleep(1)
        return None
    except Exception:
        return None

async def handle_request(request: Union[str, dict]) -> dict:
    """Handle JSON-RPC request"""
    try:
        # Parse JSON string if needed
        if isinstance(request, str):
            try:
                request = json.loads(request)
            except json.JSONDecodeError as e:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error", "data": str(e)},
                    "id": None
                }

        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if not method:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request"},
                "id": request_id,
            }

        if not isinstance(params, dict):
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": "Invalid params"},
                "id": request_id,
            }

        # Handle tools/call method
        if method == "tools/call":
            tool_name = params.get("name")
            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request"},
                    "id": request_id,
                }
            handler = globals().get(tool_name)
        else:
            handler = globals().get(f"handle_{method}")

        if not handler:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": request_id,
            }

        try:
            # For tools/call, pass the arguments directly
            if method == "tools/call":
                result = await handler(tool_name, params.get("arguments", {}))
            else:
                result = await handler(**params)

            # Check if the result indicates an error
            if isinstance(result, dict) and result.get("status") == "error":
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": result.get("message", "Internal error")
                    },
                    "id": request_id
                }

            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": str(e)
                },
                "id": request_id
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request_id
            }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request.get("id") if isinstance(request, dict) else None,
        }

async def main():
    """Main function to handle JSON-RPC requests"""
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    
    # Register signal handlers for graceful shutdown on Unix systems
    for sig_name in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(
                getattr(signal, sig_name),
                lambda sig_name=sig_name: asyncio.create_task(shutdown(sig_name))
            )
        except (NotImplementedError, AttributeError):
            # Windows doesn't support signals
            logger.warning(f"Could not add signal handler for {sig_name} (might be Windows)")
    
    try:
        logger.info("Starting KVM MCP server")
        
        while True:
            try:
                request = input()
                if not request:
                    break
                
                response = await handle_request(request)
                print(json.dumps(response))
            except EOFError:
                logger.info("Received EOF, shutting down")
                break
            except Exception as e:
                logger.error(f"Error handling request: {str(e)}")
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": str(e)}
                }))
    finally:
        # Cleanup resources
        logger.info("Cleaning up resources")
        await connection_pool.close_all()

async def shutdown(sig_name=None):
    """Cleanup handler for graceful shutdown"""
    if sig_name:
        logger.info(f"Received {sig_name}, shutting down")
    
    # Close all connections in the pool
    await connection_pool.close_all()
    
    # Cancel pending tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Stop the event loop
    loop = asyncio.get_running_loop()
    loop.stop()

if __name__ == "__main__":
    asyncio.run(main()) 