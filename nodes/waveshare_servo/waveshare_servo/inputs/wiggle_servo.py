"""Handler for the 'wiggle_servo' input event."""

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


def handle_wiggle_servo(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Handle incoming 'wiggle_servo' event.

    Extracts the servo ID from the event data and calls the `wiggle_servo`
    function to perform the action.

    Args:
        context: The node context dictionary.
        event: The Dora input event dictionary.

    Returns:
        True if the wiggle action was successful, False otherwise.
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


def wiggle_servo(context: Dict[str, Any], servo_id: int) -> bool:
    """Wiggle a specific servo for physical identification.

    Args:
        context: The node context dictionary.
        servo_id: The ID of the servo to wiggle.

    Returns:
        True if the wiggle action was successful, False otherwise.
    """
    servos = context["servos"]
    if servo_id in servos:
        servo = servos[servo_id]
        return servo.wiggle()
    return False
