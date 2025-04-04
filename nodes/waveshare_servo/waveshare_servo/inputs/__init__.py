"""
Input handlers for the Waveshare Servo Node.
"""

from .move_servo import handle_move_servo, move_servo
from .wiggle_servo import handle_wiggle_servo, wiggle_servo
from .calibrate_servo import handle_calibrate_servo, calibrate_servo
from .update_servo_setting import handle_update_servo_setting, update_servo_setting
from .tick import handle_tick, scan_for_servos
from .settings import handle_settings
from .setting_updated import handle_setting_updated
from .gamepad_event import handle_gamepad_event
from .detach_servo import handle_detach_servo, detach_servo

__all__ = [
    'handle_move_servo',
    'move_servo',
    'handle_wiggle_servo',
    'wiggle_servo',
    'handle_calibrate_servo',
    'calibrate_servo',
    'handle_update_servo_setting',
    'update_servo_setting',
    'handle_tick',
    'scan_for_servos',
    'handle_settings',
    'handle_setting_updated',
    'handle_gamepad_event',
    'handle_detach_servo',
    'detach_servo',
]