# wall-e-dora

wall-e-dora is a multi-node project based on the Dora framework designed for robotics and embedded systems integration. It brings together several components ranging from gamepad input handling to motor control firmware on Raspberry Pi Pico.

## Components

- **Gamepad Node**: Interfaces with various gamepad devices and sends input events.
- **Talker Nodes**: Broadcast messages upon receiving triggers, implemented in talker-1 and talker-2.
- **Listener Node**: Processes speech and other input messages, implemented in listener-1.
- **Tracks Firmware**: Embedded firmware for motor control using PID, with configuration for right and left motors.
- **Tracks Node**: Manages serial log processing and interacts with the firmware.

## Building and Flashing Firmware

Use the provided Makefile targets:
- make tracks/build
- make tracks/flash
- make tracks/update

## Development and Testing

- Install dependencies using pip.
- Format code using ruff.
- Run tests with pytest.

## Dataflow and Deployment

Node dataflow is defined in dataflow.yml to orchestrate inter-node communication using the Dora framework.

## Contributing

Follow the guidelines in CONVENTIONS.md for coding style and commit messages. Contributions are licensed under the MIT License.
