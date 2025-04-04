"""Broadcaster function for servo status updates."""

import json
import traceback
import sys
import os
import pyarrow as pa
from typing import Dict

# Add the parent directory to the path for imports if needed
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from waveshare_servo.servo.controller import Servo


def broadcast_servo_status(node, servo_id: int, servos: Dict[int, Servo]):
    """Broadcast the status of a single specified servo.

    Retrieves the servo's settings, converts them to a dictionary, and sends
    it as a JSON string via the 'servo_status' output.

    Args:
        node: The Dora node instance.
        servo_id: The ID of the servo whose status should be broadcast.
        servos: The dictionary mapping servo IDs to Servo objects.
    """
    try:
        if servo_id in servos:
            servo = servos[servo_id]
            node.send_output(
                "servo_status",
                pa.array([json.dumps(servo.settings.to_dict())])
            )
    except Exception as e:
        print(f"Error broadcasting servo status: {e}")
        traceback.print_exc()
