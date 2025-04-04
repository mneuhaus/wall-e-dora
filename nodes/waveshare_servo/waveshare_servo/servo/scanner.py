"""
Serial connection manager for the Waveshare Servo Node.
"""

import time
from typing import Optional, Set

import serial

from .port_finder import find_servo_port
from .discovery import discover_servos


class ServoScanner:
    """Manages serial connection and servo discovery."""

    def __init__(self):
        self.port = None
        self.serial_conn = None

    def connect(self) -> bool:
        """Connect to the servo controller."""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                return True

            self.port = find_servo_port()
            if not self.port:
                print("No servo controller found")
                return False

            # Use the same baud rate as the previous implementation (1000000)
            self.serial_conn = serial.Serial(self.port, 1000000, timeout=0.5)
            time.sleep(0.1)  # Allow time for connection to establish
            return True
        except Exception as e:
            print(f"Failed to connect to servo controller: {e}")
            return False

    def disconnect(self):
        """Disconnect from the servo controller."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def discover_servos(self) -> Set[int]:
        """Discover all connected servos."""
        if not self.connect():
            return set()
        
        return discover_servos(self.serial_conn)