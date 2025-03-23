"""
Handler for wiggle_servo events.
"""

import traceback
from typing import Dict, Any

from event_processor import extract_event_data


def handle_wiggle_servo(manager, event: Dict[str, Any]) -> bool:
    """
    Handle incoming wiggle_servo event by extracting data and wiggling the servo.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            if servo_id is not None:
                return wiggle_servo(manager, servo_id)
    except Exception as e:
        print(f"Error processing wiggle_servo event: {e}")
        traceback.print_exc()
    return False


def wiggle_servo(manager, servo_id: int) -> bool:
    """
    Wiggle a servo to help with physical identification.
    
    Args:
        manager: ServoManager instance
        servo_id: ID of the servo to wiggle
        
    Returns:
        bool: Success or failure
    """
    if servo_id in manager.servos:
        servo = manager.servos[servo_id]
        return servo.wiggle()
    return False