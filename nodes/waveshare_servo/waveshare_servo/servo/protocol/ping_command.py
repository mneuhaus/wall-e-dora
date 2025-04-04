"""Function for sending a PING command to a servo."""

import time
from typing import Optional


def send_ping_command(serial_conn, servo_id: int) -> Optional[str]:
    """Send a PING command using the SCS binary protocol.

    Args:
        serial_conn: The PySerial connection object.
        servo_id: The ID of the servo to ping.

    Returns:
        "OK" if a response is received, None otherwise.
    """
    try:
        # Ping command
        cmd = bytearray([0xFF, 0xFF, servo_id, 2, 1])
        checksum = (~sum(cmd[2:]) & 0xFF)
        cmd.append(checksum)
        serial_conn.write(cmd)
        serial_conn.flush()
        time.sleep(0.05)
        binary_response = serial_conn.read(serial_conn.in_waiting)
        if binary_response:
            return "OK"
        return None
    except Exception as e:
        print(f"Error sending ping command to servo {servo_id}: {e}")
        return None
