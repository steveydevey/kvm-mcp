import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import asyncio
import signal
import sys
import json
from datetime import datetime

from .config.config import config
from .connection.pool import connection_pool
from .cache.vm_cache import vm_info_cache
from .vm.management import list_vms, start_vm, stop_vm, reboot_vm, get_vm_ip
from .vm.creation import create_vm

def console_print(message: str, message_type: str = "info") -> None:
    """Print a formatted message to the console stderr"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = {
        "info": "\033[94m",  # Blue
        "success": "\033[92m",  # Green
        "warning": "\033[93m",  # Yellow
        "error": "\033[91m",  # Red
    }.get(message_type, "\033[0m")  # Default/Reset
    
    print(f"{color}[{timestamp}] {message}\033[0m", file=sys.stderr, flush=True)

# Configure logging
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'kvm_mcp.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('kvm_mcp')

async def handle_request(request_str: str) -> str:
    """Handle a JSON-RPC request"""
    try:
        request = json.loads(request_str)
        
        if request["method"] == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "1.0",
                    "serverInfo": {
                        "name": "kvm-control"
                    }
                }
            }
        elif request["method"] == "tools/call":
            tool_name = request["params"]["name"]
            arguments = request["params"]["arguments"]
            
            if tool_name == "list_vms":
                result = await list_vms(**arguments)
            elif tool_name == "start_vm":
                result = await start_vm(**arguments)
            elif tool_name == "stop_vm":
                result = await stop_vm(**arguments)
            elif tool_name == "reboot_vm":
                result = await reboot_vm(**arguments)
            elif tool_name == "create_vm":
                result = await create_vm(**arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": result
            }
        else:
            raise ValueError(f"Unknown method: {request['method']}")
        
        return json.dumps(response)
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": request.get("id", None),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
        return json.dumps(error_response)

async def shutdown(sig_name=None):
    """Clean shutdown of the server"""
    if sig_name:
        console_print(f'Received exit signal {sig_name}', "warning")
    
    console_print('Shutting down...', "warning")
    
    # Close all libvirt connections
    await connection_pool.close_all()
    
    # Clear caches
    vm_info_cache.invalidate()
    
    console_print('Cleanup completed', "success")

async def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown(sig.name))
        )
    
    console_print("KVM MCP Server starting...", "info")
    console_print("Waiting for JSON-RPC requests...", "info")
    console_print("Press Ctrl+C to stop the server", "info")
    
    try:
        # Read requests from stdin and write responses to stdout
        while True:
            request = await loop.run_in_executor(None, sys.stdin.readline)
            if not request:
                break
                
            response = await handle_request(request)
            print(response, flush=True)
    except Exception as e:
        console_print(f'Server error: {str(e)}', "error")
        await shutdown()
    finally:
        console_print('Server stopped', "warning")
        # Remove signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig) 