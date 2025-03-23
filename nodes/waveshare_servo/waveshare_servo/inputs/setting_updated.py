"""
Handler for setting_updated events.
"""

import traceback
from typing import Dict, Any, Optional

from event_processor import extract_event_data


def handle_setting_updated(manager, event: Dict[str, Any]) -> bool:
    """Handle setting_updated event."""
    try:
        data, error = extract_event_data(event)
        if data and isinstance(data, dict):
            path = data.get("path", "")
            value = data.get("value")
            
            if path and value is not None:
                manager.config.handle_settings_updated(path, value)
                
                # Check if this is a servo setting that needs to be applied
                parts = path.split(".")
                if len(parts) >= 3 and parts[0] == "servo":
                    try:
                        servo_id = int(parts[1])
                        property_name = parts[2]
                        
                        # Apply the setting if the servo exists
                        if servo_id in manager.servos and hasattr(
                            manager.servos[servo_id].settings, property_name
                        ):
                            setattr(
                                manager.servos[servo_id].settings, property_name, value
                            )
                            
                            # If this is a position update, actually move the servo
                            if property_name == "position":
                                manager.servos[servo_id].move(value)
                    except (ValueError, IndexError):
                        pass
            return True
    except Exception as e:
        print(f"Error processing setting_updated event: {e}")
    return False
