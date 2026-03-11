"""Servo discovery utility for the Waveshare Servo Node."""

from __future__ import annotations

from typing import Set

from .registers import DISCOVERY_MAX_ID, DISCOVERY_MIN_ID
from .sdk import COMM_SUCCESS


def discover_servos(port_handler, packet_handler) -> Set[int]:
    """Discover connected servos by pinging the configured ID range."""
    if not port_handler or not port_handler.is_open:
        return set()

    try:
        port_handler.is_using = False
        if port_handler.ser and port_handler.ser.is_open:
            port_handler.ser.reset_input_buffer()
    except Exception as exc:
        print(f"Discovery pre-scan cleanup failed: {exc}")
        return set()

    discovered: Set[int] = set()
    for servo_id in range(DISCOVERY_MIN_ID, DISCOVERY_MAX_ID + 1):
        try:
            port_handler.is_using = False
            _, result, _ = packet_handler.ping(port_handler, servo_id)
            if result == COMM_SUCCESS:
                discovered.add(servo_id)
        except Exception as exc:
            print(f"Error while pinging servo {servo_id}: {exc}")
            port_handler.is_using = False

    return discovered
