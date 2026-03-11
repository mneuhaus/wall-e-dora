"""Handler for the `clone_servo` input event."""

from __future__ import annotations

import traceback
from typing import Any, Dict

from waveshare_servo.outputs.servo_status import broadcast_servo_status
from waveshare_servo.utils.event_processor import extract_event_data


def handle_clone_servo(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Clone EEPROM settings from one servo to another."""
    try:
        data, error = extract_event_data(event)
        if data:
            source_id = data.get("source_id")
            target_id = data.get("target_id")
            if source_id is not None and target_id is not None:
                return clone_servo(context, int(source_id), int(target_id))
    except Exception as exc:
        print(f"Error processing clone_servo event: {exc}")
        traceback.print_exc()
    return False


def clone_servo(context: Dict[str, Any], source_id: int, target_id: int) -> bool:
    """Clone settings from source servo to target servo."""
    node = context["node"]
    config = context["config"]
    servos = context["servos"]

    if source_id == target_id:
        print("Cannot clone a servo onto itself")
        return False

    source_servo = servos.get(source_id)
    target_servo = servos.get(target_id)
    if source_servo is None or target_servo is None:
        return False

    success, skipped = target_servo.clone_settings_from(source_id)
    if not success:
        print(f"Failed to clone servo settings from {source_id} to {target_id}: {skipped}")
        return False

    target_servo.read_model_info()
    target_servo.read_status()
    target_config = target_servo.read_config()
    if target_config is not None:
        target_servo.settings.min_pulse = target_config.min_angle
        target_servo.settings.max_pulse = target_config.max_angle
        target_servo.settings.calibrated = target_config.max_angle > target_config.min_angle

    config.update_servo_settings(target_servo.settings)
    broadcast_servo_status(node, target_id, servos)
    print(
        f"Cloned servo settings {source_id} -> {target_id}. "
        f"Skipped: {', '.join(skipped) if skipped else 'none'}"
    )
    return True
