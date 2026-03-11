"""Serial connection manager and servo discovery for the Waveshare Servo Node."""

from __future__ import annotations

import time
from typing import Set

from .discovery import discover_servos
from .port_finder import find_servo_port
from .registers import DEFAULT_BAUDRATE, PROTOCOL_END
from .sdk import PacketHandler, PortHandler


class ServoScanner:
    """Manages the serial connection and performs servo discovery."""

    def __init__(self):
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
        """Establish a serial connection to the servo controller."""
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
                print("Failed to open servo port")
                return False

            if not self.port_handler.setBaudRate(DEFAULT_BAUDRATE):
                print("Failed to set servo baud rate")
                self.port_handler.closePort()
                return False

            time.sleep(0.1)
            return True
        except Exception as exc:
            print(f"Failed to connect to servo controller: {exc}")
            return False

    def disconnect(self) -> None:
        """Close the serial connection if it is open."""
        if self.port_handler and self.port_handler.is_open:
            self.port_handler.closePort()

    def discover_servos(self) -> Set[int]:
        """Discover all connected servos by pinging them."""
        if not self.connect():
            return set()
        return discover_servos(self.port_handler, self.packet_handler)
