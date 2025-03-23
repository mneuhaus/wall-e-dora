"""
Text-based command for servo protocol.
"""

import time
from typing import Optional


def send_text_command(serial_conn, servo_id: int, command: str) -> Optional[str]:
    """Send a command using text protocol format."""
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