"""
Handler for update_servo_setting events.
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

from waveshare_servo.event_processor import extract_event_data
from waveshare_servo.outputs.servo_status import broadcast_servo_status


def handle_update_servo_setting(context, event: Dict[str, Any]) -> bool:
    """
    Handle incoming update_servo_setting event by extracting data and updating the servo setting.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            property_name = data.get("property")
            value = data.get("value")
            if all(x is not None for x in [servo_id, property_name, value]):
                return update_servo_setting(context, servo_id, property_name, value)
    except Exception as e:
        print(f"Error processing update_servo_setting event: {e}")
        traceback.print_exc()
    return False


def update_servo_setting(context, servo_id: int, property_name: str, value: any) -> bool:
    """
    Update a specific setting for a servo.
    
    Args:
        context: Node context dictionary
        servo_id: ID of the servo to update
        property_name: Name of the property to update
        value: New value for the property
        
    Returns:
        bool: Success or failure
    """
    node = context["node"]
    config = context["config"]
    servos = context["servos"]
    
    if servo_id in servos:
        servo = servos[servo_id]
        
        # Update the setting in the servo object
        if hasattr(servo.settings, property_name):
            setattr(servo.settings, property_name, value)
            
            # Special handling for some properties
            if property_name == "invert" and value:
                # Recalculate position for inverted servo
                current_pos = servo.settings.position
                inverted_pos = servo.settings.max_pulse - (current_pos - servo.settings.min_pulse)
                servo.settings.position = inverted_pos
            
            # Update config node
            config.update_servo_setting(servo_id, property_name, value)
            
            # Broadcast updated status
            broadcast_servo_status(node, servo_id, servos)
            return True
    return False