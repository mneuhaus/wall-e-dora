"""Handler for tick events."""

import traceback
from typing import Dict, Any

from waveshare_servo.servo.models import ServoSettings
from waveshare_servo.servo.controller import Servo
from waveshare_servo.outputs.servo_status import broadcast_servo_status
from waveshare_servo.outputs.servos_list import broadcast_servos_list


def handle_tick(context, event: Dict[str, Any]) -> bool:
    """Handle tick event by scanning for servos."""
    try:
        scan_for_servos(context)
        return True
    except Exception as e:
        print(f"Error processing tick event: {e}")
        traceback.print_exc()
        return False


def scan_for_servos(context):
    """Scan for servos, assign new IDs if necessary, and initialize them."""
    try:
        node = context["node"]
        scanner = context["scanner"]
        config = context["config"]
        servos = context["servos"]

        if "next_available_id" not in context:
            all_known_ids = set()
            try:
                all_known_ids = set(config.get_all_servo_ids())
            except Exception:
                pass
            start_id = 2
            if all_known_ids:
                start_id = max(max(all_known_ids) + 1, start_id)
            context["next_available_id"] = start_id

        next_available_id = context["next_available_id"]
        previously_known_servos = set(servos.keys())

        # Discover servos
        discovered_ids = set()
        try:
            discovered_ids = scanner.discover_servos()
            if discovered_ids and discovered_ids != previously_known_servos:
                print(f"Discovered servo IDs: {discovered_ids}")
        except Exception as scan_error:
            print(f"Error during servo discovery: {scan_error}")

        current_servos = set(servos.keys())

        # Process newly discovered servos
        newly_discovered_ids = discovered_ids - current_servos
        if newly_discovered_ids:
            print(f"New servos detected: {newly_discovered_ids}")

        for discovered_id in newly_discovered_ids:
            servo_to_add_id = discovered_id
            settings = None

            settings_dict = config.get_servo_settings(discovered_id)

            if settings_dict:
                settings = ServoSettings(**settings_dict)
                settings.id = discovered_id
            else:
                print(f"New servo ID {discovered_id} detected. Creating default settings.")
                settings = ServoSettings(id=discovered_id)

                if discovered_id == 1:
                    while next_available_id in current_servos or next_available_id in discovered_ids:
                        next_available_id += 1

                    new_id = next_available_id
                    print(f"Default ID 1 servo detected. Assigning new ID: {new_id}")

                    temp_settings = ServoSettings(id=1)
                    temp_servo = Servo(
                        scanner.port_handler, scanner.packet_handler, temp_settings
                    )

                    try:
                        if temp_servo.set_id(new_id):
                            print(f"ID change successful: 1 -> {new_id}")
                            settings.id = new_id
                            servo_to_add_id = new_id
                            next_available_id += 1
                            context["next_available_id"] = next_available_id
                        else:
                            print(f"ERROR: Failed to set ID {new_id} for servo with ID 1.")
                            continue
                    except Exception as e:
                        print(f"ERROR: Exception during set_id: {e}")
                        traceback.print_exc()
                        continue

                config.update_servo_settings(settings)

            if servo_to_add_id in servos:
                continue

            servos[servo_to_add_id] = Servo(
                scanner.port_handler, scanner.packet_handler, settings
            )

            broadcast_servo_status(node, servo_to_add_id, servos)

        # Check for disconnected servos
        # Skip disconnect logic if discovery returned empty (likely transient failure)
        if discovered_ids:
            disconnected_ids = previously_known_servos - discovered_ids
            if disconnected_ids:
                print(f"Servos disconnected: {disconnected_ids}")
                for servo_id in disconnected_ids:
                    if servo_id in servos:
                        del servos[servo_id]
        elif previously_known_servos:
            print(f"Discovery returned empty but {len(previously_known_servos)} servos were previously known - skipping disconnect")

        # Broadcast servo list
        if set(servos.keys()) != previously_known_servos:
            print(f"Broadcasting updated servos list: {list(servos.keys())}")
        broadcast_servos_list(node, servos)

    except Exception as e:
        print(f"Error during scan_for_servos: {e}")
        traceback.print_exc()
