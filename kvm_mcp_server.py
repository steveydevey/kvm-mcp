import libvirt
import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
import asyncio
import json
import subprocess
import time
from typing import Union

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
async def list_vms(name: str, arguments: dict) -> list:
    """List all available virtual machines"""
    try:
        conn = libvirt.open('qemu:///system')
        if conn is None:
            return [{"error": "Failed to connect to libvirt daemon"}]
        
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
                # If we can't get some info about a domain, still include it with what we know
                result.append({
                    'name': domain.name(),
                    'state': 'unknown',
                    'error': str(e)
                })
        
        conn.close()
        return result
    except libvirt.libvirtError as e:
        return [{"error": str(e)}]

@server.call_tool()
async def start_vm(name: str, arguments: dict) -> dict:
    """Start a virtual machine by name"""
    try:
        vm_name = arguments.get("name")
        if not vm_name:
            return {"status": "error", "message": "VM name not provided"}
        
        conn = libvirt.open('qemu:///system')
        if conn is None:
            return {"status": "error", "message": "Failed to connect to libvirt daemon"}
        
        domain = conn.lookupByName(vm_name)
        state, reason = domain.state()
        
        if state == libvirt.VIR_DOMAIN_RUNNING:
            return {"status": "error", "message": f"VM {vm_name} is already running"}
        
        if domain.create() == 0:
            result = {"status": "success", "message": f"VM {vm_name} started successfully"}
        else:
            result = {"status": "error", "message": f"Failed to start VM {vm_name}"}
        
        conn.close()
        return result
    except libvirt.libvirtError as e:
        return {"status": "error", "message": str(e)}

@server.call_tool()
async def stop_vm(name: str, arguments: dict) -> dict:
    """Stop a virtual machine by name"""
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
            return {"status": "error", "message": f"VM {vm_name} is already stopped"}
        
        if domain.shutdown() == 0:
            result = {"status": "success", "message": f"VM {vm_name} stopped successfully"}
        else:
            result = {"status": "error", "message": f"Failed to stop VM {vm_name}"}
        
        conn.close()
        return result
    except libvirt.libvirtError as e:
        return {"status": "error", "message": str(e)}

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
        network = arguments.get("network", "default")
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
        disk_path = f"/var/lib/libvirt/images/{vm_name}.qcow2"
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
                <interface type='network'>
                    <source network='{network}'/>
                    <model type='virtio'/>
                </interface>
                <graphics type='vnc' port='-1' autoport='yes'/>
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
        
        # Get list of running VMs
        result = subprocess.run(['virsh', 'list', '--name'], capture_output=True, text=True)
        if result.returncode != 0:
            return {"status": "error", "message": "Failed to get VM list", "error": result.stderr}
        
        vms = [vm.strip() for vm in result.stdout.splitlines() if vm.strip()]
        vnc_ports = {}
        
        # Get VNC port for each VM
        for vm in vms:
            port_result = subprocess.run(['virsh', 'vncdisplay', vm], capture_output=True, text=True)
            if port_result.returncode == 0 and port_result.stdout.strip():
                port = port_result.stdout.strip()
                # Convert display number to actual port (e.g., ":1" -> 5901)
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
    while True:
        try:
            request = input()
            if not request:
                break
            response = await handle_request(request)
            print(json.dumps(response))
        except EOFError:
            break
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32000, "message": str(e)}
            }))

async def handle_create_vm(name: str, memory: int, vcpus: int, disk_size: int, network: str) -> dict:
    """Create a new VM"""
    try:
        # Validate parameters
        if not name or not isinstance(name, str):
            raise ValueError("Invalid VM name")
        if not isinstance(memory, int) or memory < 256:
            raise ValueError("Memory must be at least 256MB")
        if not isinstance(vcpus, int) or vcpus < 1:
            raise ValueError("Must have at least 1 vCPU")
        if not isinstance(disk_size, int) or disk_size < 1:
            raise ValueError("Disk size must be at least 1GB")
        if not network or not isinstance(network, str):
            raise ValueError("Invalid network name")

        # Create VM using libvirt
        conn = libvirt.open("qemu:///system")
        if conn is None:
            raise Exception("Failed to connect to libvirt")

        # Create VM configuration
        xml = f"""
        <domain type='kvm'>
            <name>{name}</name>
            <memory unit='MiB'>{memory}</memory>
            <vcpu>{vcpus}</vcpu>
            <os>
                <type arch='x86_64' machine='pc'>hvm</type>
                <boot dev='hd'/>
            </os>
            <devices>
                <disk type='file' device='disk'>
                    <driver name='qemu' type='qcow2'/>
                    <source file='/var/lib/libvirt/images/{name}.qcow2'/>
                    <target dev='vda' bus='virtio'/>
                </disk>
                <interface type='network'>
                    <source network='{network}'/>
                    <model type='virtio'/>
                </interface>
                <graphics type='vnc' port='-1' autoport='yes'/>
            </devices>
        </domain>
        """

        # Create VM
        dom = conn.defineXML(xml)
        if dom is None:
            raise Exception("Failed to define VM")

        # Start VM
        if dom.create() < 0:
            raise Exception("Failed to start VM")

        return {"status": "success", "message": f"VM {name} created successfully"}

    except Exception as e:
        raise Exception(f"Failed to create VM: {str(e)}")

async def handle_delete_vm(name: str) -> dict:
    """Delete a VM"""
    try:
        if not name or not isinstance(name, str):
            raise ValueError("Invalid VM name")

        conn = libvirt.open("qemu:///system")
        if conn is None:
            raise Exception("Failed to connect to libvirt")

        dom = conn.lookupByName(name)
        if dom is None:
            raise Exception(f"VM {name} not found")

        # Destroy VM if running
        if dom.isActive():
            dom.destroy()

        # Undefine VM
        dom.undefine()

        return {"status": "success", "message": f"VM {name} deleted successfully"}

    except Exception as e:
        raise Exception(f"Failed to delete VM: {str(e)}")

async def handle_list_vms() -> dict:
    """List all VMs"""
    try:
        conn = libvirt.open("qemu:///system")
        if conn is None:
            raise Exception("Failed to connect to libvirt")

        domains = conn.listAllDomains()
        vms = []

        for dom in domains:
            vms.append({
                "name": dom.name(),
                "state": dom.state()[0],
                "memory": dom.maxMemory(),
                "vcpus": dom.maxVcpus()
            })

        return {"vms": vms}

    except Exception as e:
        raise Exception(f"Failed to list VMs: {str(e)}")

async def handle_get_vm_info(name: str) -> dict:
    """Get detailed information about a VM"""
    try:
        if not name or not isinstance(name, str):
            raise ValueError("Invalid VM name")

        conn = libvirt.open("qemu:///system")
        if conn is None:
            raise Exception("Failed to connect to libvirt")

        dom = conn.lookupByName(name)
        if dom is None:
            raise Exception(f"VM {name} not found")

        info = dom.info()
        return {
            "name": dom.name(),
            "state": info[0],
            "memory": info[1],
            "vcpus": info[3],
            "cpu_time": info[4]
        }

    except Exception as e:
        raise Exception(f"Failed to get VM info: {str(e)}")

async def handle_initialize(protocolVersion: str = "1.0", capabilities: dict = None, clientInfo: dict = None) -> dict:
    """Handle initialization request"""
    return {
        "protocolVersion": protocolVersion,
        "serverInfo": {
            "name": "kvm-control",
            "version": "1.0.0"
        },
        "capabilities": {
            "vmManagement": True,
            "networkManagement": True,
            "storageManagement": True
        }
    }

if __name__ == "__main__":
    asyncio.run(main()) 