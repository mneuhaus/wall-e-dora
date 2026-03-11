"""Handler for the `calibrate_servo` input event."""

from __future__ import annotations

import traceback
from typing import Any, Dict

from waveshare_servo.outputs.servo_status import broadcast_servo_status
from waveshare_servo.utils.event_processor import extract_event_data



def handle_calibrate_servo(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Extract the requested servo ID and run auto-calibration."""
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            if servo_id is not None:
                return calibrate_servo(context, int(servo_id))
    except Exception as exc:
        print(f"Error processing calibrate_servo event: {exc}")
        traceback.print_exc()
    return False



def calibrate_servo(context: Dict[str, Any], servo_id: int) -> bool:
    """Auto-calibrate a servo using stall detection."""
    node = context["node"]
    config = context["config"]
    servos = context["servos"]

    servo = servos.get(servo_id)
    if servo is None:
        return False

    print(f"Starting auto-calibration for servo {servo_id}")
    limits = servo.auto_calibrate()
    if not limits:
        print(f"Auto-calibration failed for servo {servo_id}")
        return False

    min_limit, max_limit = limits
    servo.settings.min_pulse = min_limit
    servo.settings.max_pulse = max_limit
    servo.settings.calibrated = True

    center = (min_limit + max_limit) // 2
    servo.move(center)
    servo.read_status()
    config.update_servo_settings(servo.settings)
    broadcast_servo_status(node, servo_id, servos)

    print(f"Auto-calibration complete for servo {servo_id}: {min_limit}-{max_limit}")
    return True
