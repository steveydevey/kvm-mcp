#!/bin/bash

# Resume VM
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "start_vm", "arguments": {"name": "maggie"}}, "id": 1}' | python3 kvm_mcp_server.py

# Get VNC ports
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_vnc_ports", "arguments": {}}, "id": 1}' | python3 kvm_mcp_server.py 