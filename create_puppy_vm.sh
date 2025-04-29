#!/bin/bash

# Send initialization request
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0", "capabilities": {}, "clientInfo": {"name": "test-client"}}, "id": 1}' | python3 kvm_mcp_server.py
 
# Send VM creation request with minimal parameters, using defaults from config
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "create_vm", "arguments": {}}, "id": 2}' | python3 kvm_mcp_server.py 