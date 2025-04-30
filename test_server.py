import json
import subprocess
import sys

def send_request(method, params):
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    # Start the server process
    server = subprocess.Popen(
        ["python3", "kvm_mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send the request
    server.stdin.write(json.dumps(request) + "\n")
    server.stdin.flush()
    
    # Get the response
    response = server.stdout.readline()
    
    # Clean up
    server.terminate()
    server.wait()
    
    return json.loads(response)

if __name__ == "__main__":
    # Test list_vms
    print("Testing list_vms...")
    response = send_request("tools/call", {
        "name": "handle_list_vms",
        "arguments": {}
    })
    print(json.dumps(response, indent=2)) 