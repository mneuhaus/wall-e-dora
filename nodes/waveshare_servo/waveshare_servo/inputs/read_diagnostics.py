"""Handler for on-demand `read_servo_diagnostics` requests."""

from __future__ import annotations

import time
import traceback
from typing import Any, Dict

from waveshare_servo.outputs.servo_diagnostics import broadcast_servo_diagnostics
from waveshare_servo.utils.event_processor import extract_event_data


def handle_read_diagnostics(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Read and broadcast diagnostics for one servo or the full attached set."""
    try:
        data, _ = extract_event_data(event)
        if not data:
            return False

        if data.get("all"):
            return read_all_diagnostics(context)

        servo_id = data.get("id")
        if servo_id is not None:
            return read_diagnostics(context, int(servo_id))
    except Exception as exc:
        print(f"Error processing read_servo_diagnostics event: {exc}")
        traceback.print_exc()
    return False


def _build_diagnostics_payload(servo_id: int, servo) -> dict[str, Any]:
    """Build a structured diagnostics payload for a single servo."""
    model = servo.read_model_info()
    status = servo.read_status()
    config = servo.read_config()

    return {
        "id": servo_id,
        "alias": servo.settings.alias,
        "timestamp": int(time.time()),
        "model": model.to_dict() if model else None,
        "status": status.to_dict() if status else None,
        "config": config.to_dict() if config else None,
    }


def read_diagnostics(context: Dict[str, Any], servo_id: int) -> bool:
    """Read model, status, and config from a specific servo."""
    node = context["node"]
    servos = context["servos"]
    servo = servos.get(servo_id)
    if servo is None:
        return False

    payload = _build_diagnostics_payload(servo_id, servo)
    broadcast_servo_diagnostics(node, payload)
    return True


def read_all_diagnostics(context: Dict[str, Any]) -> bool:
    """Read diagnostics for all attached servos and broadcast them together."""
    node = context["node"]
    servos = context["servos"]

    payloads = [
        _build_diagnostics_payload(servo_id, servo)
        for servo_id, servo in sorted(servos.items())
        if servo is not None
    ]
    if not payloads:
        return False

    broadcast_servo_diagnostics(node, payloads)
    return True
