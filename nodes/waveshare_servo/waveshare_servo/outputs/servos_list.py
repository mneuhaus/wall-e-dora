"""Broadcaster for the list of discovered servos."""

from __future__ import annotations

import traceback
from typing import Dict

import pyarrow as pa

from waveshare_servo.servo.controller import Servo



def broadcast_servos_list(node, servos: Dict[int, Servo]) -> None:
    """Broadcast the list of responsive servos as an Arrow object array."""
    try:
        found_servos = []
        for servo in servos.values():
            if servo.is_responsive():
                found_servos.append(servo.settings.to_transport_dict())

        sorted_servos = sorted(
            found_servos,
            key=lambda settings: (
                settings.get("alias", "").lower() if settings.get("alias") else "zzz",
                settings.get("id", 0),
            ),
        )
        node.send_output("servos_list", pa.array(sorted_servos))
        print(f"Broadcasting {len(sorted_servos)} found servos out of {len(servos)} configured")
    except Exception as exc:
        print(f"Error broadcasting servos list: {exc}")
        traceback.print_exc()
