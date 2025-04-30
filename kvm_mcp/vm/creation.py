import os
import json
import logging
import subprocess
import tempfile
from typing import Dict

from .ignition import generate_ignition_config

logger = logging.getLogger('kvm_mcp')

async def create_vm(arguments: dict) -> Dict:
    """Create a new CoreOS VM using virt-install as per Fedora CoreOS documentation"""
    try:
        # Extract parameters from arguments
        vm_name = arguments.get("name")
        memory = arguments.get("memory")
        vcpus = arguments.get("vcpus")
        disk_size = arguments.get("disk_size", 20)
        network = arguments.get("network", "brforvms")
        master_image = arguments.get("master_image")
        ignition = arguments.get("ignition")
        os_variant = arguments.get("os_variant", "fedora-coreos-stable")

        # Validate parameters
        if not vm_name or not isinstance(vm_name, str):
            return {"status": "error", "message": "Invalid VM name"}
        if any(c in "!@#$%^&*()+={}[]|\\:;\"'<>?/" for c in vm_name):
            return {"status": "error", "message": "VM name contains invalid characters"}
        if not isinstance(memory, int) or memory < 256:
            return {"status": "error", "message": "Memory must be at least 256MB"}
        if memory > 1024 * 1024:
            return {"status": "error", "message": "Memory exceeds maximum limit of 1TB"}
        if not isinstance(vcpus, int) or vcpus < 1:
            return {"status": "error", "message": "Must have at least 1 vCPU"}
        if vcpus > 128:
            return {"status": "error", "message": "vCPUs exceed maximum limit of 128"}
        if not isinstance(disk_size, int) or disk_size < 1:
            return {"status": "error", "message": "Disk size must be at least 1GB"}
        if disk_size > 10000:
            return {"status": "error", "message": "Disk size exceeds maximum limit of 10TB"}
        if not network or not isinstance(network, str):
            return {"status": "error", "message": "Invalid network name"}
        if not master_image or not os.path.exists(master_image):
            return {"status": "error", "message": f"Master image {master_image} does not exist"}
        if not ignition or not isinstance(ignition, dict):
            return {"status": "error", "message": "Ignition config must be provided as a dict"}

        # Prepare disk path
        disk_path = f"/vm/{vm_name}.qcow2"
        if os.path.exists(disk_path):
            return {"status": "error", "message": f"Disk image {disk_path} already exists"}

        # Create disk image with backing file
        result = subprocess.run([
            "qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", master_image, disk_path, f"{disk_size}G"
        ], capture_output=True, text=True)
        if result.returncode != 0:
            return {"status": "error", "message": f"Failed to create disk image: {result.stderr}"}

        # Generate and write Ignition config to a temp file
        try:
            ignition_config = generate_ignition_config(vm_name, ignition)
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".ign") as ign_file:
                ign_file.write(ignition_config)
                ign_path = ign_file.name

            # Set SELinux context if needed (Fedora/SELinux hosts)
            try:
                subprocess.run(["chcon", "--verbose", "--type", "svirt_home_t", ign_path], check=False)
            except Exception:
                pass

            # Build virt-install command
            virtinstall_cmd = [
                "virt-install",
                "--connect=qemu:///system",
                f"--name={vm_name}",
                f"--memory={memory}",
                f"--vcpus={vcpus}",
                f"--os-variant={os_variant}",
                "--import",
                f"--disk=path={disk_path},format=qcow2,bus=virtio",
                f"--network=bridge={network},model=virtio",
                "--graphics=vnc,listen=0.0.0.0",
                f"--qemu-commandline=optargs='-fw_cfg name=opt/com.coreos/config,file={ign_path}'"
            ]

            # Run virt-install
            result = subprocess.run(virtinstall_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # Clean up temp ignition file
                os.unlink(ign_path)
                return {"status": "error", "message": f"virt-install failed: {result.stderr}"}

            # Clean up temp ignition file
            os.unlink(ign_path)
            return {"status": "success", "message": f"VM {vm_name} created successfully using virt-install"}

        except Exception as e:
            # Clean up temp ignition file if it exists
            if 'ign_path' in locals():
                try:
                    os.unlink(ign_path)
                except:
                    pass
            return {"status": "error", "message": f"Error during VM creation: {str(e)}"}

    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"} 