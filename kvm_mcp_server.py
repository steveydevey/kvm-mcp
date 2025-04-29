import libvirt
import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
import asyncio
import json

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(config_path) as f:
        return json.load(f)

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

def generate_ignition_config(vm_name: str, arguments: dict) -> str:
    """Generate an Ignition configuration for Fedora CoreOS"""
    try:
        # Get configuration values
        hostname = arguments.get("hostname", config["vm"]["ignition"]["default_hostname"])
        user = arguments.get("user", config["vm"]["ignition"]["default_user"])
        timezone = arguments.get("timezone", config["vm"]["ignition"]["default_timezone"])
        locale = arguments.get("locale", config["vm"]["ignition"]["default_locale"])
        
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
    except Exception as e:
        raise Exception(f"Failed to generate Ignition config: {str(e)}")

@server.call_tool()
async def create_vm(name: str, arguments: dict) -> dict:
    """Create a new virtual machine using virt-install or from a master image"""
    try:
        # Required parameters
        vm_name = arguments.get("name", config["vm"]["default_name"])
        memory = arguments.get("memory", config["vm"]["default_memory"])
        vcpus = arguments.get("vcpus", config["vm"]["default_vcpus"])
        disk_size = arguments.get("disk_size", config["vm"]["default_disk_size"])
        os_variant = arguments.get("os_variant", config["vm"]["default_os_variant"])
        
        # Optional parameters
        location = arguments.get("location")  # URL for network installation
        cdrom = arguments.get("cdrom", config["vm"]["default_iso"])  # Path to ISO
        extra_args = arguments.get("extra_args", "")
        master_image = arguments.get("master_image", config["vm"]["default_master_image"])  # Path to master qcow2 image
        
        # Ensure VM directory exists
        os.makedirs(config["vm"]["disk_path"], exist_ok=True)
        
        if master_image:
            # Create VM from master image
            if not os.path.exists(master_image):
                return {"status": "error", "message": f"Master image {master_image} not found"}
            
            # Create a copy of the master image
            import subprocess
            disk_path = os.path.join(config["vm"]["disk_path"], f"{vm_name}.qcow2")
            result = subprocess.run(["qemu-img", "create", "-f", "qcow2", "-b", master_image, disk_path], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Failed to create disk image for VM {vm_name}",
                    "error": result.stderr
                }
            
            # Generate Ignition config
            try:
                ignition_config = generate_ignition_config(vm_name, arguments)
                ignition_path = os.path.join(config["vm"]["disk_path"], f"{vm_name}.ign")
                with open(ignition_path, 'w') as f:
                    f.write(ignition_config)
            except Exception as e:
                return {"status": "error", "message": str(e)}
            
            # Create VM definition
            xml = f"""<domain type='kvm'>
                <name>{vm_name}</name>
                <memory unit='MiB'>{memory}</memory>
                <vcpu placement='static'>{vcpus}</vcpu>
                <os>
                    <type arch='x86_64' machine='pc-q35-7.2'>hvm</type>
                    <boot dev='hd'/>
                </os>
                <features>
                    <acpi/>
                    <apic/>
                    <vmport state='off'/>
                </features>
                <cpu mode='host-model' check='partial'/>
                <clock offset='utc'/>
                <on_poweroff>destroy</on_poweroff>
                <on_reboot>restart</on_reboot>
                <on_crash>destroy</on_crash>
                <devices>
                    <emulator>/usr/bin/qemu-system-x86_64</emulator>
                    <disk type='file' device='disk'>
                        <driver name='qemu' type='qcow2'/>
                        <source file='{disk_path}'/>
                        <target dev='vda' bus='virtio'/>
                    </disk>
                    <interface type='bridge'>
                        <source bridge='{config["vm"]["default_network"]}'/>
                        <model type='virtio'/>
                    </interface>
                    <graphics type='vnc' port='-1' listen='0.0.0.0'/>
                    <console type='pty'/>
                </devices>
                <qemu:commandline>
                    <qemu:arg value='-fw_cfg'/>
                    <qemu:arg value='name=opt/com.coreos/config,file={ignition_path}'/>
                </qemu:commandline>
            </domain>"""
            
            # Define and start the VM
            conn = libvirt.open('qemu:///system')
            if conn is None:
                return {"status": "error", "message": "Failed to connect to libvirt daemon"}
            
            try:
                domain = conn.defineXML(xml)
                if domain.create() == 0:
                    return {
                        "status": "success",
                        "message": f"VM {vm_name} created and started successfully from master image"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to start VM {vm_name}"
                    }
            finally:
                conn.close()
        else:
            # Original installation-based VM creation
            cmd = [
                "virt-install",
                f"--name={vm_name}",
                f"--memory={memory}",
                f"--vcpus={vcpus}",
                f"--disk=path={os.path.join(config['vm']['disk_path'], f'{vm_name}.qcow2')},size={disk_size}",
                f"--os-variant={os_variant}",
                f"--network=bridge={config['vm']['default_network']},model=virtio",
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
                return {"status": "error", "message": "Either location, cdrom, or master_image must be provided"}
            
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