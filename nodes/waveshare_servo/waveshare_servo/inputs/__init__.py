"""
Input handlers for the Waveshare Servo Node.
"""

from .move_servo import handle_move_servo, move_servo
from .wiggle_servo import handle_wiggle_servo, wiggle_servo
from .calibrate_servo import handle_calibrate_servo, calibrate_servo
from .update_servo_setting import handle_update_servo_setting, update_servo_setting
from .tick import handle_tick
from .settings import handle_settings
from .setting_updated import handle_setting_updated

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
    'handle_settings',
    'handle_setting_updated',
]