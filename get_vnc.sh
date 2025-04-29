#!/bin/bash

# Send initialization request
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0", "capabilities": {}, "clientInfo": {"name": "test-client"}}, "id": 1}' | python3 kvm_mcp_server.py

# Get VNC ports for all running VMs
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_vnc_ports", "arguments": {}}, "id": 2}' | python3 kvm_mcp_server.py 