"""
Handler for move_servo events.
"""

import traceback
from typing import Dict, Any
import sys
import os

# Add the parent directory to the path for imports if needed
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from waveshare_servo.utils.event_processor import extract_event_data
from waveshare_servo.outputs.servo_status import broadcast_servo_status


def handle_move_servo(context, event: Dict[str, Any]) -> bool:
    """
    Handle incoming move_servo event by extracting data and moving the servo.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            position = data.get("position")
            if servo_id is not None and position is not None:
                return move_servo(context, servo_id, position)
    except Exception as e:
        print(f"Error processing move_servo event: {e}")
        traceback.print_exc()
    return False


def move_servo(context, servo_id: int, position: int) -> bool:
    """
    Move a servo to a specific position.
    
    Args:
        context: Node context dictionary
        servo_id: ID of the servo to move
        position: Target position
        
    Returns:
        bool: Success or failure
    """
    node = context["node"]
    config = context["config"]
    servos = context["servos"]
    
    if servo_id in servos:
        servo = servos[servo_id]
        if servo.move(position):
            # Update position in config
            config.update_servo_setting(servo_id, "position", position)
            broadcast_servo_status(node, servo_id, servos)
            return True
    return False