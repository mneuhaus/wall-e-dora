"""
Calibration operation for servos.
"""

import time


def calibrate_servo(servo):
    """Calibrate the servo min/max values."""
    try:
        # Test minimum position
        servo.send_command(f"P{servo.settings.min_pulse}T{servo.settings.speed}")
        time.sleep(1)
        min_result = servo.send_command("PULSEGET")
        
        # Test maximum position
        servo.send_command(f"P{servo.settings.max_pulse}T{servo.settings.speed}")
        time.sleep(1)
        max_result = servo.send_command("PULSEGET")
        
        if min_result and max_result:
            servo.settings.calibrated = True
            return True
        return False
    except Exception as e:
        print(f"Error calibrating servo {servo.id}: {e}")
        return False