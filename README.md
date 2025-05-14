[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/steveydevey-kvm-mcp-badge.png)](https://mseep.ai/app/steveydevey-kvm-mcp)

# KVM MCP Server

A powerful JSON-RPC server for managing KVM virtual machines through a simple and intuitive interface. This server provides a centralized way to control and monitor your KVM virtual machines using a standardized protocol.

## Why This Project?

Managing KVM virtual machines typically requires using multiple command-line tools like `virsh`, `virt-install`, and `qemu-system`. This project aims to:

1. **Simplify VM Management**: Provide a single, unified interface for all VM operations
2. **Enable Remote Control**: Allow remote management of VMs through JSON-RPC
3. **Automate VM Operations**: Make it easy to script and automate VM management tasks
4. **Standardize VM Configuration**: Ensure consistent VM setup across your infrastructure
5. **Optimize Performance**: Implement efficient resource management and caching strategies

## Features

- **VM Lifecycle Management**:
  - Create new VMs with customizable parameters
  - Start/stop/reboot VMs
  - List all available VMs with their status
  - Automatic state tracking and recovery

- **Network Management**:
  - Configure VM networking using bridges
  - Support for the `brforvms` bridge
  - Automatic network interface configuration
  - IP address tracking and management

- **Storage Management**:
  - Configurable VM disk storage location
  - Support for various disk formats (qcow2)
  - Configurable disk sizes
  - Automatic disk cleanup and management

- **Display Management**:
  - VNC support for graphical access
  - Automatic VNC port assignment
  - Tools to find and connect to VM displays
  - Display state tracking and recovery

- **Installation Support**:
  - Network installation from ISO images
  - Local installation from CDROM
  - Support for various OS variants
  - Automated installation configuration

- **Performance Optimizations**:
  - Connection pooling for libvirt to reduce connection overhead
  - VM information caching for improved responsiveness
  - Asynchronous processing for better concurrency
  - Advanced logging for diagnostics and troubleshooting
  - Graceful shutdown handling for proper resource cleanup
  - Automatic connection recovery and validation
  - Rate limiting for API operations
  - Performance metrics collection

## Performance Benefits

### Connection Pooling
- **Reduced Latency**: Eliminates the overhead of repeatedly opening and closing libvirt connections
- **Resource Efficiency**: Maintains a pool of reusable connections, reducing system resource usage
- **Automatic Recovery**: Detects and replaces dead connections automatically
- **Configurable Pool Size**: Adjust the number of connections based on your workload

### Caching
- **Faster Response Times**: Reduces repeated queries to libvirt for common operations
- **Configurable TTL**: Set cache expiration based on your needs
- **Selective Bypass**: Option to bypass cache for operations requiring fresh data
- **Automatic Invalidation**: Cache is automatically invalidated when VM states change

### Asynchronous Processing
- **Improved Concurrency**: Handle multiple requests simultaneously
- **Better Resource Utilization**: Efficient use of system resources
- **Non-blocking Operations**: Long-running operations don't block the server
- **Graceful Shutdown**: Proper cleanup of resources during shutdown

### Monitoring and Diagnostics
- **Structured Logging**: Easy-to-parse log format for analysis
- **Performance Metrics**: Track operation timing and resource usage
- **Error Tracking**: Detailed error logging for troubleshooting
- **Resource Monitoring**: Track connection pool usage and cache effectiveness

## Configuration

The server uses a JSON configuration file (`config.json`) to store default values and paths. This makes the server more portable and easier to customize. The configuration includes:

```json
{
    "vm": {
        "disk_path": "/vm",                    // Base directory for VM disk storage
        "default_iso": "/iso/ubuntu-24.04.2-live-server-amd64.iso",  // Default installation media for Ubuntu-based VMs
        "default_master_image": "/iso/fedora-coreos-41-qemu.x86_64.qcow2",  // Default base image for Fedora CoreOS VMs
        "default_name": "newvmname",           // Default VM name
        "default_memory": 2048,                // Default memory allocation in MB
        "default_vcpus": 2,                    // Default number of virtual CPUs
        "default_disk_size": 20,               // Default disk size in GB
        "default_os_variant": "generic",       // Default OS variant for virt-install
        "default_network": "brforvms",         // Default network bridge for VM networking
        "ignition": {                          // Fedora CoreOS specific configuration
            "default_hostname": "coreos",      // Default hostname for CoreOS VMs
            "default_user": "core",            // Default user for CoreOS VMs
            "default_ssh_key": "~/.ssh/id_rsa.pub",  // Default SSH public key path
            "default_timezone": "UTC",         // Default timezone
            "default_locale": "en_US.UTF-8",   // Default system locale
            "default_password_hash": null      // Optional: Default password hash for user
        }
    }
}
```

You can modify these values to match your environment's requirements. The configuration supports environment variable overrides using the following format:
- `VM_DISK_PATH` for `disk_path`
- `VM_DEFAULT_ISO` for `default_iso`
- `VM_DEFAULT_MASTER_IMAGE` for `default_master_image`
- `VM_DEFAULT_NAME` for `default_name`
- `VM_DEFAULT_MEMORY` for `default_memory`
- `VM_DEFAULT_VCPUS` for `default_vcpus`
- `VM_DEFAULT_DISK_SIZE` for `default_disk_size`
- `VM_DEFAULT_OS_VARIANT` for `default_os_variant`
- `VM_DEFAULT_NETWORK` for `default_network`
- `VM_IGNITION_DEFAULT_HOSTNAME` for `ignition.default_hostname`
- `VM_IGNITION_DEFAULT_USER` for `ignition.default_user`
- `VM_IGNITION_DEFAULT_SSH_KEY` for `ignition.default_ssh_key`
- `VM_IGNITION_DEFAULT_TIMEZONE` for `ignition.default_timezone`
- `VM_IGNITION_DEFAULT_LOCALE` for `ignition.default_locale`
- `VM_IGNITION_DEFAULT_PASSWORD_HASH` for `ignition.default_password_hash`

## Performance Tuning

### Connection Pool Configuration
```python
connection_pool = LibvirtConnectionPool(
    max_connections=5,     # Maximum number of connections in the pool
    timeout=30,            # Timeout for getting a connection (seconds)
    uri='qemu:///system'   # Libvirt connection URI
)
```

### Cache Configuration
```python
vm_info_cache = VMInfoCache(
    max_size=50,           # Maximum number of VMs to cache
    ttl=60                 # Time-to-live for cache entries (seconds)
)
```

### Logging Configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'kvm_mcp.log',
            maxBytes=10485760,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
```

## Getting Started

### Prerequisites

- Python 3.6 or higher
- KVM and libvirt installed on the host system
- The network bridge configured (default: `brforvms`)
- VM storage directory created (default: `/vm/`)
- Sufficient system resources for your VM workload

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/kvm-mcp.git
   cd kvm-mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the server:
   - Edit `config.json` to match your environment
   - Ensure all required directories exist
   - Verify network bridge configuration
   - Adjust performance settings as needed

### Usage

1. Start the server:
   ```bash
   python3 kvm_mcp_server.py
   ```

2. Send commands using JSON-RPC. Example scripts are provided:
   - `create_vm.sh`: Create a new VM using default configuration
   - `get_vnc_ports.sh`: Find VNC ports for running VMs

## Example Commands

### Create a New VM
```bash
./create_vm.sh
```
This will create a new VM using the default configuration from `config.json`. You can override any of these defaults by providing them in the request.

### Find VNC Ports
```bash
./get_vnc_ports.sh
```
This will show all running VMs and their VNC ports, making it easy to connect to their displays.

### List VMs with Cache Bypass
```bash
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_vms", "arguments": {"no_cache": true}}, "id": 1}' | python3 kvm_mcp_server.py
```

## Monitoring and Troubleshooting

### Log Files
- `kvm_mcp.log`: Current log file
- `kvm_mcp.log.1`: Previous log file (rotated)
- Logs include timing information, connection pool status, and cache hits/misses

### Performance Metrics
- Connection pool usage statistics
- Cache hit/miss ratios
- Operation timing metrics
- Resource utilization statistics

### Common Issues and Solutions

1. **Connection Pool Exhaustion**
   - Symptom: Slow response times or connection errors
   - Solution: Increase `max_connections` in the connection pool configuration

2. **Cache Invalidation Issues**
   - Symptom: Stale VM information
   - Solution: Use `no_cache` parameter or reduce cache TTL

3. **Resource Cleanup**
   - Symptom: Resource leaks or connection issues
   - Solution: Ensure proper shutdown using SIGTERM or SIGINT

## Project Structure

- `kvm_mcp_server.py`: Main server implementation
- `config.json`: Configuration file
- `requirements.txt`: Python dependencies
- Example scripts in the root directory
- Test suite in the `tests/` directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 