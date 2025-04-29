#!/bin/bash

# Check if VM already exists
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_vms", "arguments": {"connection": "qemu:///system"}}, "id": 0}' | python3 kvm_mcp_server.py | grep -q '"xeon"'
if [ $? -eq 0 ]; then
    echo "Error: VM 'xeon' already exists. Please choose a different name or remove the existing VM first."
    exit 1
fi

# Send initialization request
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0", "capabilities": {}, "clientInfo": {"name": "test-client"}}, "id": 1}' | python3 kvm_mcp_server.py

# Create VM using master CoreOS image
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "create_vm", "arguments": {"name": "xeon", "memory": 2048, "vcpus": 2, "disk_size": 20, "os_variant": "fedora-coreos", "master_image": "/iso/fedora-coreos-41-qemu.x86_64.qcow2", "ignition": {"hostname": "xeon", "user": "core", "ssh_key": "~/.ssh/id_rsa.pub", "timezone": "UTC", "locale": "en_US.UTF-8"}, "connection": "qemu:///system"}}, "id": 2}' | python3 kvm_mcp_server.py

# Wait a moment for the VM to start
sleep 2

# Get VNC ports
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_vnc_ports", "arguments": {"connection": "qemu:///system"}}, "id": 3}' | python3 kvm_mcp_server.py

# Stop the VM to ensure hostname changes take effect
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "stop_vm", "arguments": {"name": "xeon", "connection": "qemu:///system"}}, "id": 4}' | python3 kvm_mcp_server.py

# Wait a moment
sleep 2

# Start the VM again
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "start_vm", "arguments": {"name": "xeon", "connection": "qemu:///system"}}, "id": 5}' | python3 kvm_mcp_server.py 