"""Broadcaster for the list of discovered servos."""

import json
import traceback
import pyarrow as pa
from typing import Dict

# Assuming editable install handles path correctly
from waveshare_servo.servo.controller import Servo


def broadcast_servos_list(node, servos: Dict[int, Servo]):
    """Broadcast the list of discovered and responsive servos.

    Filters the provided servo dictionary to include only those servos that
    respond to a PING command, then sorts them by alias (case-insensitive)
    and then by ID. The resulting list is sent as a JSON string via the
    'servos_list' output.

    Args:
        node: The Dora node instance used for sending output.
        servos: A dictionary mapping servo IDs to Servo objects.
    """
    try:
        # Filter out servos that aren't actually found by checking connection
        found_servos = []
        for servo in servos.values():
            # Test if servo is responsive by sending a ping command
            response = servo.send_command("PING")
            if response and "OK" in response:
                found_servos.append(servo.settings.to_dict())
        
        # Sort servos by alias first (case-insensitive), then by ID
        sorted_servos = sorted(
            found_servos,
            key=lambda s: (
                s.get('alias', '').lower() if s.get('alias') else 'zzz',  # Empty aliases sort last
                s.get('id', 0)
            )
        )
        
        # Only send servos that responded to ping, in sorted order
        node.send_output(
            "servos_list", 
            pa.array([json.dumps(sorted_servos)])
        )
        print(f"Broadcasting {len(sorted_servos)} found servos out of {len(servos)} configured")
    except Exception as e:
        print(f"Error broadcasting servos list: {e}")
        traceback.print_exc()
