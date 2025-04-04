"""Function for sending text-based commands to servos."""

import time
from typing import Optional


def send_text_command(serial_conn, servo_id: int, command: str) -> Optional[str]:
    """Send a command using the text-based protocol format.

    Formats the command as '#<ID><COMMAND>\r\n' and sends it over the
    serial connection. Reads and returns the response line.

    Args:
        serial_conn: The PySerial connection object.
        servo_id: The target servo ID.
        command: The command string (e.g., "PING", "PULSEGET").

    Returns:
        The response string from the servo, or None on error.
    """
    try:
        # Fallback to text format for other commands
        full_command = f"#{servo_id}{command}\r\n"
        serial_conn.write(full_command.encode())
        serial_conn.flush()
        time.sleep(0.1)
        response = serial_conn.readline().decode().strip()
        return response
    except Exception as e:
        print(f"Error sending text command to servo {servo_id}: {e}")
        return None
