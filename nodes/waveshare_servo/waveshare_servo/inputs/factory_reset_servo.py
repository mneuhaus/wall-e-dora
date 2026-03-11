"""Handler for the `factory_reset_servo` input event."""

from __future__ import annotations

import time
import traceback
from typing import Any, Dict

from waveshare_servo.inputs.tick import scan_for_servos
from waveshare_servo.utils.event_processor import extract_event_data



def handle_factory_reset_servo(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Factory-reset a servo and trigger re-discovery."""
    try:
        data, error = extract_event_data(event)
        if data:
            servo_id = data.get("id")
            if servo_id is not None:
                return factory_reset_servo(context, int(servo_id))
    except Exception as exc:
        print(f"Error processing factory_reset_servo event: {exc}")
        traceback.print_exc()
    return False



def factory_reset_servo(context: Dict[str, Any], servo_id: int) -> bool:
    """Reset a servo, clear persisted settings, and rescan the bus."""
    config = context["config"]
    servos = context["servos"]

    servo = servos.get(servo_id)
    if servo is None:
        return False

    success, skipped = servo.factory_reset()
    if not success:
        print(f"Factory reset failed for servo {servo_id}: {skipped}")
        return False

    config.delete_servo_settings(servo_id)
    servos.pop(servo_id, None)
    time.sleep(0.2)
    scan_for_servos(context)
    print(
        f"Factory reset complete for servo {servo_id}. "
        f"Skipped: {', '.join(skipped) if skipped else 'none'}"
    )
    return True
