#!/bin/bash

# Send initialization request
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0", "capabilities": {}, "clientInfo": {"name": "test-client"}}, "id": 1}' | python3 kvm_mcp_server.py

# Send VM creation request
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "create_vm", "arguments": {"name": "puppy", "memory": 2048, "vcpus": 2, "disk_size": 20, "os_variant": "generic", "cdrom": "/iso/ubuntu-24.04.2-live-server-amd64.iso"}}, "id": 2}' | python3 kvm_mcp_server.py 