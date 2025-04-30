import libvirt
import logging
import subprocess
import json
from typing import Dict, Optional

from ..connection.pool import connection_pool
from ..cache.vm_cache import vm_info_cache
from ..utils.decorators import timing_decorator

logger = logging.getLogger('kvm_mcp')

@timing_decorator
async def list_vms(use_cache: bool = True) -> list:
    """List all available virtual machines"""
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
                
                vm_info = {
                    "name": domain.name(),
                    "id": domain.ID(),
                    "state": state_str,
                    "autostart": domain.autostart(),
                    "persistent": domain.isPersistent()
                }
                result.append(vm_info)
            except libvirt.libvirtError as e:
                logger.error(f"Error getting info for domain {domain.name()}: {str(e)}")
    
    if use_cache:
        vm_info_cache.set("_all_vms_", result)
    return result

@timing_decorator
async def start_vm(vm_name: str) -> Dict:
    """Start a virtual machine"""
    async with connection_pool.get_connection() as conn:
        try:
            domain = conn.lookupByName(vm_name)
            if domain.isActive():
                return {"success": False, "error": "VM is already running"}
            
            domain.create()
            vm_info_cache.invalidate(vm_name)
            vm_info_cache.invalidate("_all_vms_")
            
            return {"success": True, "message": f"VM {vm_name} started successfully"}
        except libvirt.libvirtError as e:
            return {"success": False, "error": f"Failed to start VM: {str(e)}"}

@timing_decorator
async def stop_vm(vm_name: str, force: bool = False) -> Dict:
    """Stop a virtual machine"""
    async with connection_pool.get_connection() as conn:
        try:
            domain = conn.lookupByName(vm_name)
            if not domain.isActive():
                return {"success": False, "error": "VM is not running"}
            
            if force:
                domain.destroy()
            else:
                domain.shutdown()
            
            vm_info_cache.invalidate(vm_name)
            vm_info_cache.invalidate("_all_vms_")
            
            return {"success": True, "message": f"VM {vm_name} {'destroyed' if force else 'shutdown'} successfully"}
        except libvirt.libvirtError as e:
            return {"success": False, "error": f"Failed to stop VM: {str(e)}"}

@timing_decorator
async def reboot_vm(vm_name: str) -> Dict:
    """Reboot a virtual machine"""
    async with connection_pool.get_connection() as conn:
        try:
            domain = conn.lookupByName(vm_name)
            if not domain.isActive():
                return {"success": False, "error": "VM is not running"}
            
            domain.reboot()
            vm_info_cache.invalidate(vm_name)
            vm_info_cache.invalidate("_all_vms_")
            
            return {"success": True, "message": f"VM {vm_name} rebooted successfully"}
        except libvirt.libvirtError as e:
            return {"success": False, "error": f"Failed to reboot VM: {str(e)}"}

def get_vm_ip(domain) -> Optional[str]:
    """Get the IP address of a VM using virsh domifaddr"""
    try:
        cmd = ["virsh", "domifaddr", domain.name()]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to get VM IP: {result.stderr}")
            return None
        
        # Parse the output to find the IP address
        lines = result.stdout.strip().split('\n')
        if len(lines) < 3:  # Need at least header + separator + data
            return None
        
        for line in lines[2:]:  # Skip header and separator
            parts = line.split()
            if len(parts) >= 4:
                ip = parts[3].split('/')[0]  # Remove CIDR notation if present
                return ip
        
        return None
    except Exception as e:
        logger.error(f"Error getting VM IP: {str(e)}")
        return None 