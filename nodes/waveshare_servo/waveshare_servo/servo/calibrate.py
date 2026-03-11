"""Compatibility calibration helper for the servo controller."""

from __future__ import annotations


def calibrate_servo(servo) -> bool:
    """Run auto-calibration and update the servo object's software limits."""
    limits = servo.auto_calibrate()
    if not limits:
        return False

    servo.settings.min_pulse, servo.settings.max_pulse = limits
    servo.settings.calibrated = True
    return True
