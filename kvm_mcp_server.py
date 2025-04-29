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