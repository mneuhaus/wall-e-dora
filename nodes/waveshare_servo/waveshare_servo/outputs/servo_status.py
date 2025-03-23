"""
Broadcaster for servo status updates.
"""

import json
import traceback
import pyarrow as pa
from typing import Dict
from servo import Servo


def broadcast_servo_status(node, servo_id: int, servos: Dict[int, Servo]):
    """Broadcast the status of a single servo."""
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