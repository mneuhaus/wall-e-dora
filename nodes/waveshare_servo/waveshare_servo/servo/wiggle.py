"""
Wiggle operation for servo identification.
"""

import time


def wiggle_servo(servo, wiggle_range=100, iterations=2):
    """Wiggle a servo for identification."""
    try:
        current_pos = servo.settings.position
        # Move to slight left and right of current position
        for _ in range(iterations):  # Wiggle multiple times
            positions = [
                current_pos - wiggle_range,
                current_pos,
                current_pos + wiggle_range,
                current_pos,
            ]
            for pos in positions:
                safe_pos = max(
                    servo.settings.min_pulse, min(servo.settings.max_pulse, pos)
                )
                servo.move(safe_pos)
                time.sleep(0.2)
        return True
    except Exception as e:
        print(f"Error wiggling servo {servo.id}: {e}")
        return False