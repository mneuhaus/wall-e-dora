"""Serial connection manager and servo discovery for the Waveshare Servo Node."""

import time
from typing import Optional, Set

from .port_finder import find_servo_port
from .discovery import discover_servos
from .sdk import PortHandler, PacketHandler

BAUDRATE = 1000000
PROTOCOL_END = 1


class ServoScanner:
    """Manages the serial connection and performs servo discovery."""

    def __init__(self):
        """Initialize the ServoScanner."""
        self.port = None
        self.port_handler = None
        self.packet_handler = None

    @property
    def serial_conn(self):
        """Backward-compatible access to the underlying serial connection."""
        if self.port_handler and self.port_handler.is_open:
            return self.port_handler.ser
        return None

    def connect(self) -> bool:
        """Establish a serial connection to the servo controller.

        Returns:
            True if the connection was successful, False otherwise.
        """
        try:
            if self.port_handler and self.port_handler.is_open:
                return True

            self.port = find_servo_port()
            if not self.port:
                print("No servo controller found")
                return False

            self.port_handler = PortHandler(self.port)
            self.packet_handler = PacketHandler(PROTOCOL_END)

            if not self.port_handler.openPort():
                print("Failed to open port")
                return False

            if not self.port_handler.setBaudRate(BAUDRATE):
                print("Failed to set baud rate")
                self.port_handler.closePort()
                return False

            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"Failed to connect to servo controller: {e}")
            return False

    def disconnect(self):
        """Close the serial connection if it's open."""
        if self.port_handler and self.port_handler.is_open:
            self.port_handler.closePort()

    def discover_servos(self) -> Set[int]:
        """Discover all connected servos by pinging them.

        Returns:
            A set of IDs of the discovered servos.
        """
        if not self.connect():
            return set()

        return discover_servos(self.port_handler, self.packet_handler)
