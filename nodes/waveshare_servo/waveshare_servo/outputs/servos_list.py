"""
Broadcaster for complete servos list.
"""

import json
import traceback
import pyarrow as pa
from typing import Dict
from servo import Servo


def broadcast_servos_list(node, servos: Dict[int, Servo]):
    """Broadcast the list of all servos."""
    try:
        servo_list = [servo.settings.to_dict() for servo in servos.values()]
        node.send_output(
            "servos_list", 
            pa.array([json.dumps(servo_list)])
        )
    except Exception as e:
        print(f"Error broadcasting servos list: {e}")
        traceback.print_exc()