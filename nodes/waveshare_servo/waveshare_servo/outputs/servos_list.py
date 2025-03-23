"""
Broadcaster for complete servos list.
"""

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