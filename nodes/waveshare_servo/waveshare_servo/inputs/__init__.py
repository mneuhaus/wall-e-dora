"""Input handlers for the Waveshare Servo Node."""

from .calibrate_servo import calibrate_servo, handle_calibrate_servo
from .clone_servo import clone_servo, handle_clone_servo
from .detach_servo import detach_servo, handle_detach_servo
from .factory_reset_servo import factory_reset_servo, handle_factory_reset_servo
from .gamepad_event import handle_gamepad_event
from .move_servo import handle_move_servo, move_servo
from .read_diagnostics import handle_read_diagnostics, read_diagnostics
from .setting_updated import handle_setting_updated
from .settings import handle_settings
from .tick import handle_tick, scan_for_servos
from .update_servo_setting import handle_update_servo_setting, update_servo_setting
from .wiggle_servo import handle_wiggle_servo, wiggle_servo

__all__ = [
    "calibrate_servo",
    "clone_servo",
    "detach_servo",
    "factory_reset_servo",
    "handle_calibrate_servo",
    "handle_clone_servo",
    "handle_detach_servo",
    "handle_factory_reset_servo",
    "handle_gamepad_event",
    "handle_move_servo",
    "handle_read_diagnostics",
    "handle_setting_updated",
    "handle_settings",
    "handle_tick",
    "handle_update_servo_setting",
    "handle_wiggle_servo",
    "move_servo",
    "read_diagnostics",
    "scan_for_servos",
    "update_servo_setting",
    "wiggle_servo",
]
