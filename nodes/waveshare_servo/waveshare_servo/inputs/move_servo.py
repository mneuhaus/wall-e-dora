"""
Handler for move_servo events.
"""

import traceback
from typing import Dict, Any

from event_processor import extract_event_data
from outputs import broadcast_servo_status


def handle_move_servo(manager, event: Dict[str, Any]) -> bool:
    """
    Handle incoming move_servo event by extracting data and moving the servo.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            position = data.get("position")
            if servo_id is not None and position is not None:
                return move_servo(manager, servo_id, position)
    except Exception as e:
        print(f"Error processing move_servo event: {e}")
        traceback.print_exc()
    return False


def move_servo(manager, servo_id: int, position: int) -> bool:
    """
    Move a servo to a specific position.
    
    Args:
        manager: ServoManager instance
        servo_id: ID of the servo to move
        position: Target position
        
    Returns:
        bool: Success or failure
    """
    if servo_id in manager.servos:
        servo = manager.servos[servo_id]
        if servo.move(position):
            # Update position in config
            manager.config.update_servo_setting(servo_id, "position", position)
            broadcast_servo_status(manager.node, servo_id, manager.servos)
            return True
    return False