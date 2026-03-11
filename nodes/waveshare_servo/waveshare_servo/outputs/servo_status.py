"""Broadcaster function for single-servo status updates."""

from __future__ import annotations

import traceback
from typing import Dict

import pyarrow as pa

from waveshare_servo.servo.controller import Servo



def broadcast_servo_status(node, servo_id: int, servos: Dict[int, Servo]) -> None:
    """Broadcast the status of a single servo as an Arrow object array."""
    try:
        if servo_id not in servos:
            return
        servo = servos[servo_id]
        node.send_output("servo_status", pa.array([servo.settings.to_transport_dict()]))
    except Exception as exc:
        print(f"Error broadcasting servo status: {exc}")
        traceback.print_exc()
