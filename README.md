# KVM MCP Server

This is an MCP (Model Context Protocol) server implementation for controlling KVM/QEMU virtual machines remotely.

## Prerequisites

- Python 3.8 or higher
- libvirt and libvirt-python installed
- KVM/QEMU installed and configured
- Proper permissions to access the libvirt daemon

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have the necessary system packages:
```bash
sudo dnf install libvirt-devel python3-libvirt
```

3. Make sure your user is in the libvirt group:
```bash
sudo usermod -a -G libvirt $(whoami)
```

4. Start and enable the libvirtd service:
```bash
sudo systemctl enable --now libvirtd
```

## Usage

1. Start the MCP server:
```bash
python kvm_mcp_server.py
```

The server provides the following capabilities:

- List all available virtual machines
- Start a virtual machine
- Stop a virtual machine
- Reboot a virtual machine

## Security Considerations

- The server connects to the local libvirt daemon using the system URI
- Ensure proper permissions are set for the libvirt daemon
- Consider using TLS for remote connections if needed

## API Endpoints

- `list_vms`: Lists all available virtual machines
- `start_vm`: Starts a virtual machine by name
- `stop_vm`: Stops a virtual machine by name
- `reboot_vm`: Reboots a virtual machine by name

## Error Handling

The server includes error handling for common libvirt operations and will return appropriate error messages when operations fail. 