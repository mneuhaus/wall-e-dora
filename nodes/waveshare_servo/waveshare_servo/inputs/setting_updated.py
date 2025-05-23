"""Handler for the 'setting_updated' input event."""

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


def handle_setting_updated(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Handle the 'setting_updated' input event.

    Processes notifications about specific setting changes from the config node.
    Updates the local configuration cache and applies relevant changes to
    the corresponding servo object if applicable (e.g., updating speed or
    moving the servo if the position setting changed).

    Args:
        context: The node context dictionary.
        event: The Dora input event dictionary containing the updated setting path and value.

    Returns:
        True if the event was processed successfully, False otherwise.
    """
    try:
        config = context["config"]
        servos = context["servos"]
        
        data, error = extract_event_data(event)
        if data and isinstance(data, dict):
            path = data.get("path", "")
            value = data.get("value")
            
            if path and value is not None:
                config.handle_settings_updated(path, value)
                
                # Check if this is a servo setting that needs to be applied
                parts = path.split(".")
                if len(parts) >= 3 and parts[0] == "servo":
                    try:
                        servo_id = int(parts[1])
                        property_name = parts[2]
                        
                        # Apply the setting if the servo exists
                        if servo_id in servos and hasattr(
                            servos[servo_id].settings, property_name
                        ):
                            setattr(
                                servos[servo_id].settings, property_name, value
                            )
                            
                            # If this is a position update, actually move the servo
                            if property_name == "position":
                                servos[servo_id].move(value)
                    except (ValueError, IndexError):
                        pass
            return True
    except Exception as e:
        print(f"Error processing setting_updated event: {e}")
    return False
