"""Function for sending an ID change command to a servo."""

import time
from typing import Optional


def send_id_command(serial_conn, servo_id: int, new_id: int) -> Optional[str]:
    """Send a command to change the servo's ID using the SCS binary protocol.

    Args:
        serial_conn: The PySerial connection object.
        servo_id: The current ID of the servo.
        new_id: The new ID to assign (must be between 1 and 31).

    Returns:
        "OK" if the command was sent successfully, None otherwise.
    """
    try:
        if 1 <= new_id <= 31:
            addr = 5  # ID address
            cmd = bytearray([0xFF, 0xFF, servo_id, 4, 3, addr, new_id])
            checksum = (~sum(cmd[2:]) & 0xFF)
            cmd.append(checksum)
            serial_conn.write(cmd)
            serial_conn.flush()
            time.sleep(0.1)
            return "OK"
        return None
    except Exception as e:
        print(f"Error sending ID command to servo {servo_id}: {e}")
        return None
