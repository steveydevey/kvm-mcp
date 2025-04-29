{
  echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0"}}, "id": 1}'
  echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_vms", "arguments": {}}, "id": 2}'
} | python3 kvm_mcp_server.py 