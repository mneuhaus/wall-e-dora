"""Handler for the 'detach_servo' input event."""

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


def handle_detach_servo(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Handle incoming 'detach_servo' event.

    Extracts the servo ID from the event data and calls the `detach_servo`
    function to remove its gamepad control mapping.

    Args:
        context: The node context dictionary.
        event: The Dora input event dictionary.

    Returns:
        True if the servo was successfully detached, False otherwise.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            if servo_id is not None:
                return detach_servo(context, servo_id)
    except Exception as e:
        print(f"Error processing detach_servo event: {e}")
        traceback.print_exc()
    return False


def detach_servo(context: Dict[str, Any], servo_id: int) -> bool:
    """Detach a servo from its assigned gamepad control.

    Clears the `attached_control` and `gamepad_config` settings for the
    specified servo both in the local state and in the configuration file.

    Args:
        context: The node context dictionary.
        servo_id: The ID of the servo to detach.

    Returns:
        True if the servo was found and detached successfully, False otherwise.
    """
    node = context["node"]
    config = context["config"]
    servos = context["servos"]
    
    if servo_id in servos:
        servo = servos[servo_id]
        
        print(f"Detaching servo {servo_id} from control {servo.settings.attached_control}")
        
        # Clear the attached_control
        servo.settings.attached_control = ""
        # Clear the gamepad_config
        servo.settings.gamepad_config = {}
        
        # Update config node for both properties
        config.update_servo_setting(servo_id, "attached_control", "")
        config.update_servo_setting(servo_id, "gamepad_config", {})
        
        # Broadcast updated status
        broadcast_servo_status(node, servo_id, servos)
        return True
    
    return False
