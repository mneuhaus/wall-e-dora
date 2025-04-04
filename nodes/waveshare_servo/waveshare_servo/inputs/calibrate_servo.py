"""Handler for the 'calibrate_servo' input event."""

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


def handle_calibrate_servo(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Handle incoming 'calibrate_servo' event.

    Extracts the servo ID from the event data and calls the `calibrate_servo`
    function to perform the calibration.

    Args:
        context: The node context dictionary.
        event: The Dora input event dictionary.

    Returns:
        True if the calibration was successful, False otherwise.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            if servo_id is not None:
                return calibrate_servo(context, servo_id)
    except Exception as e:
        print(f"Error processing calibrate_servo event: {e}")
        traceback.print_exc()
    return False


def calibrate_servo(context: Dict[str, Any], servo_id: int) -> bool:
    """Calibrate a specific servo by testing its min/max positions.

    Args:
        context: The node context dictionary.
        servo_id: The ID of the servo to calibrate.

    Returns:
        True if the calibration was successful, False otherwise.
    """
    node = context["node"]
    config = context["config"]
    servos = context["servos"]
    
    if servo_id in servos:
        servo = servos[servo_id]
        if servo.calibrate():
            # Update calibration status in config
            config.update_servo_setting(servo_id, "calibrated", True)
            broadcast_servo_status(node, servo_id, servos)
            return True
    return False
