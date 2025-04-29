import libvirt
import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
import asyncio
import json

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
        result = {"status": "error", "message": f"Failed to start VM {vm_name}"}
        
        if domain.create() == 0:
            result = {"status": "success", "message": f"VM {vm_name} started successfully"}
        
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
        result = {"status": "error", "message": f"Failed to stop VM {vm_name}"}
        
        if domain.shutdown() == 0:
            result = {"status": "success", "message": f"VM {vm_name} stopped successfully"}
        
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
        result = {"status": "error", "message": f"Failed to reboot VM {vm_name}"}
        
        if domain.reboot() == 0:
            result = {"status": "success", "message": f"VM {vm_name} rebooted successfully"}
        
        conn.close()
        return result
    except libvirt.libvirtError as e:
        return {"status": "error", "message": str(e)}

@server.call_tool()
async def create_vm(name: str, arguments: dict) -> dict:
    """Create a new virtual machine using virt-install"""
    try:
        # Required parameters
        vm_name = arguments.get("name")
        memory = arguments.get("memory", 2048)  # Default 2GB
        vcpus = arguments.get("vcpus", 2)      # Default 2 vCPUs
        disk_size = arguments.get("disk_size", 20)  # Default 20GB
        os_variant = arguments.get("os_variant", "generic")
        
        if not vm_name:
            return {"status": "error", "message": "VM name not provided"}
        
        # Optional parameters
        location = arguments.get("location")  # URL for network installation
        cdrom = arguments.get("cdrom")       # Path to ISO
        extra_args = arguments.get("extra_args", "")
        
        # Ensure /vm directory exists
        os.makedirs("/vm", exist_ok=True)
        
        # Build virt-install command
        cmd = [
            "virt-install",
            f"--name={vm_name}",
            f"--memory={memory}",
            f"--vcpus={vcpus}",
            f"--disk=path=/vm/{vm_name}.qcow2,size={disk_size}",
            f"--os-variant={os_variant}",
            "--network=bridge=brforvms,model=virtio",
            "--graphics=vnc,listen=0.0.0.0",
            "--console=pty,target_type=serial",
            "--noautoconsole",
            "--virt-type=kvm"
        ]
        
        # Add installation source
        if location:
            cmd.append(f"--location={location}")
        elif cdrom:
            cmd.append(f"--cdrom={cdrom}")
        else:
            return {"status": "error", "message": "Either location or cdrom must be provided"}
        
        # Add extra arguments if provided
        if extra_args:
            cmd.append(f"--extra-args={extra_args}")
        
        # Execute virt-install
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"VM {vm_name} creation started successfully",
                "output": result.stdout
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to create VM {vm_name}",
                "error": result.stderr
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
            if port_result.returncode == 0:
                port = port_result.stdout.strip()
                if port:
                    # Convert display number to actual port (e.g., ":1" -> 5901)
                    display_num = port.lstrip(':')
                    if display_num.isdigit():
                        vnc_ports[vm] = 5900 + int(display_num)
        
        return {
            "status": "success",
            "vnc_ports": vnc_ports
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def handle_request(request_str):
    request = json.loads(request_str)
    if request["method"] == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "serverInfo": {
                    "name": "kvm-control",
                    "version": "0.1.0"
                }
            }
        }
    elif request["method"] == "tools/call":
        tool_name = request["params"]["name"]
        if tool_name == "list_vms":
            result = await list_vms(tool_name, request["params"].get("arguments", {}))
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": result
            }
        elif tool_name == "create_vm":
            result = await create_vm(tool_name, request["params"].get("arguments", {}))
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": result
            }
        elif tool_name == "get_vnc_ports":
            result = await get_vnc_ports(tool_name, request["params"].get("arguments", {}))
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": result
            }
    return {"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601, "message": "Method not found"}}

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

if __name__ == "__main__":
    asyncio.run(main()) 