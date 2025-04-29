#!/bin/bash

# Check if VM name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <vm_name> [memory_mb] [vcpus]"
    echo "Example: $0 myvm 4096 4"
    exit 1
fi

VM_NAME="$1"
MEMORY="${2:-2048}"  # Default to 2048 MB if not specified
VCPUS="${3:-2}"      # Default to 2 vCPUs if not specified

# Send initialization request
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0", "capabilities": {}, "clientInfo": {"name": "test-client"}}, "id": 1}' | python3 kvm_mcp_server.py

# Create the VM
echo "{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"params\": {\"name\": \"create_vm\", \"arguments\": {\"name\": \"$VM_NAME\", \"memory\": $MEMORY, \"vcpus\": $VCPUS, \"hostname\": \"$VM_NAME\"}}, \"id\": 2}" | python3 kvm_mcp_server.py

# Wait a moment for the VM to start
sleep 2

# Get VNC port
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_vnc_ports", "arguments": {}}, "id": 3}' | python3 kvm_mcp_server.py 