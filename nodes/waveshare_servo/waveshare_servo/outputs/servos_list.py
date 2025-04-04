"""
Broadcaster for list of actually found servos, sorted by alias then ID.
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
    """Broadcast the list of only the servos that are actually found/connected, sorted by alias then ID."""
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