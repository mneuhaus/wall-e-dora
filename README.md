# wall-e-dora

wall-e-dora is a multi-node project based on the Dora framework designed for robotics and embedded systems integration. It brings together several components for power management, web interface, audio playback, and motor control capabilities.

## Components

### Active Nodes
- **Power Node**: Monitors system power metrics including voltage, current, power consumption, state of charge (SoC), and runtime. Can trigger system shutdown.
- **Web Node**: Provides a web interface for system monitoring and control. Displays power metrics and audio controls.
- **Audio Node**: Manages audio playback with volume control and sound file management.

### Development Nodes
- **Gamepad Node**: (In Development) Interfaces with gamepad devices for input control.
- **Tracks Node**: (In Development) Firmware and control system for motor management.

## System Architecture

The system uses the Dora framework for inter-node communication. Key features include:
- Real-time power monitoring and management
- Web-based control interface
- Audio playback system
- Extensible node-based architecture

## Building and Development

### Prerequisites
- Python 3.12
- Dora framework
- Additional dependencies listed in `pyproject.toml`

### Setup
1. Create a virtual environment: `python -m venv .venv`
2. Activate the environment: `source .venv/bin/activate`
3. Install dependencies using `pip`

### Building Firmware
Use the provided Makefile targets:
```bash
make tracks/build   # Build firmware
make tracks/flash   # Flash to device
make tracks/update  # Update firmware
```

## Development and Testing

- Code formatting: Use `ruff` for consistent code style
- Testing: Run tests with `pytest`
- Node development: Follow the node structure in `nodes/` directory

## Configuration

Node dataflow is defined in `dataflow.yml`. Current configuration includes:
- Power monitoring (10-second intervals)
- Web interface updates (100ms intervals)
- Audio system with volume control
- Extensible node configuration

## Contributing

Follow the guidelines in `conventions.md` for coding style and commit messages. Contributions are licensed under the MIT License.

_Last updated: February 8, 2025_
