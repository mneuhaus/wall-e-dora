"""Handler for tick events."""

from __future__ import annotations

import traceback
from typing import Any, Dict

from waveshare_servo.outputs.servo_status import broadcast_servo_status
from waveshare_servo.outputs.servos_list import broadcast_servos_list
from waveshare_servo.servo.controller import Servo
from waveshare_servo.servo.models import ServoModel, ServoSettings, ServoStatus



def _apply_model(settings: ServoSettings, model: ServoModel | None) -> None:
    """Copy model metadata into the servo settings object."""
    if model is None:
        return
    settings.model_name = model.name
    settings.model_number = model.model_number



def _apply_status(settings: ServoSettings, status: ServoStatus | None) -> None:
    """Copy live telemetry into the servo settings object."""
    if status is None:
        return
    settings.position = status.position
    settings.voltage = status.voltage
    settings.temperature = status.temperature
    settings.load = status.load
    settings.moving = status.moving



def handle_tick(context: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """Handle tick event by scanning for servos and refreshing telemetry."""
    try:
        scan_for_servos(context)
        return True
    except Exception as exc:
        print(f"Error processing tick event: {exc}")
        traceback.print_exc()
        return False



def scan_for_servos(context: Dict[str, Any]) -> None:
    """Scan for servos, initialize new ones, and refresh live status."""
    try:
        node = context["node"]
        scanner = context["scanner"]
        config = context["config"]
        servos = context["servos"]

        if not scanner.connect():
            print("Servo scanner is not connected; skipping tick scan")
            return

        if "next_available_id" not in context:
            known_ids = set(config.get_all_servo_ids())
            context["next_available_id"] = max(known_ids, default=1) + 1

        next_available_id = max(2, int(context["next_available_id"]))
        previously_known_ids = set(servos.keys())

        discovered_ids = set()
        try:
            discovered_ids = scanner.discover_servos()
            if discovered_ids and discovered_ids != previously_known_ids:
                print(f"Discovered servo IDs: {sorted(discovered_ids)}")
        except Exception as exc:
            print(f"Error during servo discovery: {exc}")

        current_ids = set(servos.keys())
        new_ids = discovered_ids - current_ids
        if new_ids:
            print(f"New servos detected: {sorted(new_ids)}")

        for discovered_id in sorted(new_ids):
            servo_to_add_id = discovered_id
            settings_dict = config.get_servo_settings(discovered_id) or {}
            settings = ServoSettings(**settings_dict) if settings_dict else ServoSettings(id=discovered_id)
            settings.id = discovered_id

            if discovered_id == 1:
                while next_available_id in current_ids or next_available_id in discovered_ids or next_available_id in servos:
                    next_available_id += 1

                temp_servo = Servo(scanner.port_handler, scanner.packet_handler, ServoSettings(id=1))
                print(f"Default ID 1 servo detected. Assigning new ID: {next_available_id}")
                if not temp_servo.set_id(next_available_id):
                    print(f"ERROR: Failed to set ID {next_available_id} for servo with ID 1")
                    continue

                settings.id = next_available_id
                servo_to_add_id = next_available_id
                context["next_available_id"] = next_available_id + 1
                next_available_id += 1

            servo = Servo(scanner.port_handler, scanner.packet_handler, settings)
            model = servo.read_model_info()
            status = servo.read_status()
            _apply_model(settings, model)
            _apply_status(settings, status)

            if model is not None:
                print(
                    f"Detected servo #{servo_to_add_id}: {model.name} "
                    f"(model {model.model_number})"
                )

            config.update_servo_settings(settings)
            servos[servo_to_add_id] = servo
            broadcast_servo_status(node, servo_to_add_id, servos)

        if discovered_ids:
            disconnected_ids = previously_known_ids - discovered_ids
            if disconnected_ids:
                print(f"Servos disconnected: {sorted(disconnected_ids)}")
                for servo_id in disconnected_ids:
                    servos.pop(servo_id, None)
        elif previously_known_ids:
            print(
                "Discovery returned no servos but active servos are already known; "
                "skipping disconnect handling"
            )

        for servo_id in sorted(list(servos.keys())):
            servo = servos.get(servo_id)
            if servo is None:
                continue

            if not servo.settings.model_name:
                _apply_model(servo.settings, servo.read_model_info())

            status = servo.read_status()
            if status is None:
                print(f"Warning: failed to refresh live status for servo {servo_id}")
                continue

            _apply_status(servo.settings, status)
            broadcast_servo_status(node, servo_id, servos)

        if set(servos.keys()) != previously_known_ids:
            print(f"Broadcasting updated servos list: {sorted(servos.keys())}")
        broadcast_servos_list(node, servos)
    except Exception as exc:
        print(f"Error during scan_for_servos: {exc}")
        traceback.print_exc()
