"""Serial connection manager and servo discovery for the Waveshare Servo Node."""

import time
from typing import Optional, Set

import serial

from .port_finder import find_servo_port
from .discovery import discover_servos


class ServoScanner:
    """Manages the serial connection and performs servo discovery."""

    def __init__(self):
        """Initialize the ServoScanner."""
        self.port = None
        self.serial_conn = None

    def connect(self) -> bool:
        """Establish a serial connection to the servo controller.

        Finds the correct serial port using `find_servo_port` and opens
        the connection with the required baud rate.

        Returns:
            True if the connection was successful, False otherwise.
        """
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
        """Close the serial connection if it's open."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def discover_servos(self) -> Set[int]:
        """Discover all connected servos by pinging them.

        Ensures a connection is established and then calls the
        `discover_servos` utility function.

        Returns:
            A set of IDs of the discovered servos.
        """
        if not self.connect():
            return set()
        
        return discover_servos(self.serial_conn)
