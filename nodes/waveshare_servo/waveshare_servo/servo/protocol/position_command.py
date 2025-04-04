"""Functions for sending and parsing servo position commands."""

import time
from typing import Optional


def send_position_command(serial_conn, servo_id: int, position: int, time_value: int) -> Optional[str]:
    """Send a position command with time parameter using SCS binary protocol.

    Writes the goal position (address 42) and optionally the moving speed
    (address 46) if `time_value` is greater than 0.

    Args:
        serial_conn: The PySerial connection object.
        servo_id: The target servo ID.
        position: The target goal position (0-1023).
        time_value: The time parameter (often interpreted as speed, 0 means max speed).

    Returns:
        "OK" if commands were sent successfully, None otherwise.
    """
    try:
        # Send as SCS format
        # Write Goal Position (address 42) for SCS servo
        addr = 42  # Position address
        cmd = bytearray([0xFF, 0xFF, servo_id, 5, 3, addr, position & 0xFF, (position >> 8) & 0xFF])
        checksum = (~sum(cmd[2:]) & 0xFF)
        cmd.append(checksum)
        serial_conn.write(cmd)
        serial_conn.flush()
        time.sleep(0.05)
        
        # Also set speed if specified
        if time_value > 0:
            addr = 46  # Speed address
            cmd = bytearray([0xFF, 0xFF, servo_id, 5, 3, addr, time_value & 0xFF, (time_value >> 8) & 0xFF])
            checksum = (~sum(cmd[2:]) & 0xFF)
            cmd.append(checksum)
            serial_conn.write(cmd)
            serial_conn.flush()
        return "OK"
    except Exception as e:
        print(f"Error sending position command to servo {servo_id}: {e}")
        return None


def parse_position_command(command: str) -> tuple[int, int]:
    """Parse a position command string in the format 'P<position>T<time>'.

    Args:
        command: The command string to parse.

    Returns:
        A tuple containing (position, time_value). Returns (0, 0) if parsing fails.
    """
    try:
        # Validate command format
        if not command.startswith('P') or 'T' not in command:
            print(f"Invalid position command format: {command}")
            return 0, 0
            
        # Extract position and time values
        try:
            position_str = command[1:command.index("T")]
            time_str = command[command.index("T")+1:]
            
            # Verify that extracted strings contain numeric values
            if not position_str.isdigit() or not time_str.isdigit():
                print(f"Non-numeric values in position command: position={position_str}, time={time_str}")
                return 0, 0
                
            position = int(position_str)
            time_value = int(time_str)
            return position, time_value
        except ValueError as e:
            print(f"Error parsing position command values: {e}")
            return 0, 0
    except Exception as e:
        print(f"Error parsing position command '{command}': {e}")
        return 0, 0
