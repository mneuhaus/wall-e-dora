"""
ID change command for servo protocol.
"""

import time
from typing import Optional


def send_id_command(serial_conn, servo_id: int, new_id: int) -> Optional[str]:
    """Send a command to change servo ID."""
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