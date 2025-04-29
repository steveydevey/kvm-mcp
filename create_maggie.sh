#!/bin/bash

# Check if VM already exists
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_vms", "arguments": {}}, "id": 1}' | python3 kvm_mcp_server.py | grep -q '"name": "maggie"'
if [ $? -eq 0 ]; then
    echo "VM maggie already exists"
    exit 1
fi

# Initialize server
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}' | python3 kvm_mcp_server.py

# Create VM with parameters
echo '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "create_vm",
        "arguments": {
            "name": "maggie",
            "memory": 2048,
            "vcpus": 2,
            "disk_size": 20,
            "os_variant": "fedora-coreos",
            "master_image": "/vm/master.qcow2",
            "ignition": {
                "hostname": "maggie",
                "user": "core",
                "ssh_key": "~/.ssh/id_rsa.pub",
                "timezone": "UTC",
                "locale": "en_US.UTF-8"
            }
        }
    },
    "id": 1
}' | python3 kvm_mcp_server.py

# Get VNC ports
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_vnc_ports", "arguments": {}}, "id": 1}' | python3 kvm_mcp_server.py 