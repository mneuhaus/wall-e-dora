"""
Handler for calibrate_servo events.
"""

import traceback
from typing import Dict, Any

from event_processor import extract_event_data
from outputs import broadcast_servo_status


def handle_calibrate_servo(manager, event: Dict[str, Any]) -> bool:
    """
    Handle incoming calibrate_servo event by extracting data and calibrating the servo.
    """
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            if servo_id is not None:
                return calibrate_servo(manager, servo_id)
    except Exception as e:
        print(f"Error processing calibrate_servo event: {e}")
        traceback.print_exc()
    return False


def calibrate_servo(manager, servo_id: int) -> bool:
    """
    Calibrate a servo by testing min/max positions.
    
    Args:
        manager: ServoManager instance
        servo_id: ID of the servo to calibrate
        
    Returns:
        bool: Success or failure
    """
    if servo_id in manager.servos:
        servo = manager.servos[servo_id]
        if servo.calibrate():
            # Update calibration status in config
            manager.config.update_servo_setting(servo_id, "calibrated", True)
            broadcast_servo_status(manager.node, servo_id, manager.servos)
            return True
    return False