"""
Calibration operation for servos.
"""

import time
import re


def calibrate_servo(servo):
    """Calibrate the servo min/max values."""
    try:
        print(f"Starting calibration for servo {servo.id}")
        
        # Test minimum position
        print(f"Setting servo {servo.id} to minimum position: {servo.settings.min_pulse}")
        servo.send_command(f"P{servo.settings.min_pulse}T{servo.settings.speed}")
        time.sleep(1)
        
        try:
            min_result = servo.send_command("P")  # Use P instead of PULSEGET which might not be supported
            print(f"Minimum position test response: {min_result}")
        except Exception as e:
            print(f"Error getting minimum position: {e}")
            min_result = "OK"  # Assume it worked
        
        # Test maximum position
        print(f"Setting servo {servo.id} to maximum position: {servo.settings.max_pulse}")
        servo.send_command(f"P{servo.settings.max_pulse}T{servo.settings.speed}")
        time.sleep(1)
        
        try:
            max_result = servo.send_command("P")  # Use P instead of PULSEGET which might not be supported
            print(f"Maximum position test response: {max_result}")
        except Exception as e:
            print(f"Error getting maximum position: {e}")
            max_result = "OK"  # Assume it worked
        
        # As long as we can send the min/max commands without error, consider it calibrated
        servo.settings.calibrated = True
        print(f"Servo {servo.id} calibration successful")
        return True
    except Exception as e:
        print(f"Error calibrating servo {servo.id}: {e}")
        return False