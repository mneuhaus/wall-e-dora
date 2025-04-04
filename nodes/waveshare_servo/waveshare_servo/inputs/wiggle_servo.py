"""
Handler for wiggle_servo events.
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


def handle_wiggle_servo(context, event: Dict[str, Any]) -> bool:
    """
    Handle incoming wiggle_servo event by extracting data and wiggling the servo.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            if servo_id is not None:
                return wiggle_servo(context, servo_id)
    except Exception as e:
        print(f"Error processing wiggle_servo event: {e}")
        traceback.print_exc()
    return False


def wiggle_servo(context, servo_id: int) -> bool:
    """
    Wiggle a servo to help with physical identification.
    
    Args:
        context: Node context dictionary
        servo_id: ID of the servo to wiggle
        
    Returns:
        bool: Success or failure
    """
    servos = context["servos"]
    
    if servo_id in servos:
        servo = servos[servo_id]
        return servo.wiggle()
    return False