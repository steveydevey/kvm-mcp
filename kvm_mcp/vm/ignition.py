import os
import json
import logging

from ..config.config import config

logger = logging.getLogger('kvm_mcp')

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
                    "path": "/etc/hosts",
                    "mode": 420,
                    "overwrite": True,
                    "contents": {
                        "source": f"data:,127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n127.0.1.1   {hostname} {hostname}.localdomain"
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