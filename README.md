# KVM MCP Server

A powerful JSON-RPC server for managing KVM virtual machines through a simple and intuitive interface. This server provides a centralized way to control and monitor your KVM virtual machines using a standardized protocol.

## Why This Project?

Managing KVM virtual machines typically requires using multiple command-line tools like `virsh`, `virt-install`, and `qemu-system`. This project aims to:

1. **Simplify VM Management**: Provide a single, unified interface for all VM operations
2. **Enable Remote Control**: Allow remote management of VMs through JSON-RPC
3. **Automate VM Operations**: Make it easy to script and automate VM management tasks
4. **Standardize VM Configuration**: Ensure consistent VM setup across your infrastructure

## Features

- **VM Lifecycle Management**:
  - Create new VMs with customizable parameters
  - Start/stop/reboot VMs
  - List all available VMs with their status

- **Network Management**:
  - Configure VM networking using bridges
  - Support for the `brforvms` bridge
  - Automatic network interface configuration

- **Storage Management**:
  - Configurable VM disk storage location
  - Support for various disk formats (qcow2)
  - Configurable disk sizes

- **Display Management**:
  - VNC support for graphical access
  - Automatic VNC port assignment
  - Tools to find and connect to VM displays

- **Installation Support**:
  - Network installation from ISO images
  - Local installation from CDROM
  - Support for various OS variants

## Configuration

The server uses a JSON configuration file (`config.json`) to store default values and paths. This makes the server more portable and easier to customize. The configuration includes:

```json
{
    "vm": {
        "disk_path": "/vm",                    // Where VM disks are stored
        "default_iso": "/iso/ubuntu-24.04.2-live-server-amd64.iso",  // Default installation media
        "default_name": "puppy",               // Default VM name
        "default_memory": 2048,                // Default memory in MB
        "default_vcpus": 2,                    // Default number of vCPUs
        "default_disk_size": 20,               // Default disk size in GB
        "default_os_variant": "generic",       // Default OS variant
        "default_network": "brforvms"          // Default network bridge
    }
}
```

You can modify these values to match your environment's requirements.

## Getting Started

### Prerequisites

- Python 3.6 or higher
- KVM and libvirt installed on the host system
- The network bridge configured (default: `brforvms`)
- VM storage directory created (default: `/vm/`)

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

## Project Structure

- `kvm_mcp_server.py`: Main server implementation
- `config.json`: Configuration file
- `requirements.txt`: Python dependencies
- Example scripts in the root directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 