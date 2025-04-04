"""
Handler for tick events.
"""

import traceback
from typing import Dict, Any
import sys
import os

# Add the parent directory to the path for imports if needed
# (Assuming these imports are correct for your project structure)
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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
        # Use traceback for more detailed error logging
        print(f"Error processing tick event: {e}")
        traceback.print_exc()
        return False


def scan_for_servos(context):
    """Scan for servos, assign new IDs if necessary, and initialize them."""
    try:
        node = context["node"]
        scanner = context["scanner"]
        config = context["config"]
        servos = context["servos"] # Dictionary of active Servo objects {id: Servo}

        # --- Initialization of next_available_id ---
        # This should ideally happen *once* when the application starts,
        # not on every tick, unless context is reset.
        # Ensure it's initialized correctly based on existing config/scan.
        # Example (might need adjustment based on your app structure):
        if "next_available_id" not in context:
             all_known_ids = set(config.get_all_servo_ids()) # Assuming config has this method
             # Scan once at start? Depends on your app lifecycle.
             # discovered_at_start = scanner.discover_servos()
             # all_known_ids.update(discovered_at_start)
             start_id = 2 # Default starting point, avoiding 1
             if all_known_ids:
                 # Ensure start_id is higher than any known ID
                 start_id = max(max(all_known_ids) + 1, start_id)
             context["next_available_id"] = start_id
             print(f"Initialized next_available_id to: {context['next_available_id']}")
        # --- End Initialization ---

        next_available_id = context["next_available_id"] # Get current value

        # Track previously known servos to detect disconnections
        previously_known_servos = set(servos.keys())
        discovered_ids = set() # Use a set for efficient checking
        try:
            discovered_ids = scanner.discover_servos()
            # Only log when there's a change in discovered IDs
            if discovered_ids and discovered_ids != previously_known_servos:
                 print(f"Discovered servo IDs: {discovered_ids}")
        except Exception as scan_error:
             print(f"Error during servo discovery: {scan_error}")
             # Decide if you want to proceed or return based on the error
             # return # Optionally exit if discovery fails critically

        current_servos = set(servos.keys()) # IDs of servos currently in our active dictionary

        # --- Process Newly Discovered Servos ---
        newly_discovered_ids = discovered_ids - current_servos
        # Only log when servos are actually detected
        if newly_discovered_ids:
             print(f"New servos detected: {newly_discovered_ids}")

        for discovered_id in newly_discovered_ids:
            servo_to_add_id = discovered_id # This might change if ID=1 is reassigned
            settings = None
            is_newly_assigned = False

            # Check config first
            settings_dict = config.get_servo_settings(discovered_id)

            if settings_dict:
                # Using existing settings
                settings = ServoSettings(**settings_dict)
                # Ensure ID in settings matches discovered ID, might be redundant
                settings.id = discovered_id
                servo_to_add_id = discovered_id
            else:
                # No config found, treat as potentially new or default ID=1
                print(f"New servo ID {discovered_id} detected. Creating default settings.")
                settings = ServoSettings(id=discovered_id) # Start with the discovered ID

                # --- Handle Default ID Assignment ---
                if discovered_id == 1:
                    # Check if the target ID is already in use by another active servo
                    while next_available_id in current_servos or next_available_id in discovered_ids:
                         next_available_id += 1

                    new_id = next_available_id
                    print(f"Default ID 1 servo detected. Assigning new ID: {new_id}")

                    # Use temporary settings with ID 1 for the command
                    temp_settings_for_id_change = ServoSettings(id=1)
                    temp_servo = Servo(scanner.serial_conn, temp_settings_for_id_change)

                    try:
                        if temp_servo.set_id(new_id):
                            print(f"ID change successful: 1 → {new_id}")
                            settings.id = new_id         # Update settings object with the new ID
                            servo_to_add_id = new_id     # Use the new ID as the key/identifier
                            next_available_id += 1       # Increment for the *next* servo
                            context["next_available_id"] = next_available_id # Store updated value back
                            is_newly_assigned = True
                        else:
                            print(f"ERROR: Failed to set ID {new_id} for servo with ID 1. Skipping.")
                            # Don't add this servo, don't save config for it
                            continue # Move to the next discovered_id
                    except Exception as id_set_error:
                         print(f"ERROR: Exception during set_id for servo 1 to {new_id}: {id_set_error}")
                         traceback.print_exc()
                         # Don't add this servo
                         continue # Move to the next discovered_id
                # --- End Handle Default ID Assignment ---

                # Save settings *only* if it's not ID 1 that failed, or if it's a non-1 ID
                config.update_servo_settings(settings)

            # --- Add the Servo to Active Dictionary ---
            # Check if the ID (potentially new) is already in the active servos dict
            # This is a safeguard, shouldn't happen if logic above is correct
            if servo_to_add_id in servos:
                 continue
            servos[servo_to_add_id] = Servo(scanner.serial_conn, settings)

            # Read initial voltage for the new servo
            try:
                 servos[servo_to_add_id].read_voltage()
            except Exception as voltage_error:
                 print(f"Warning: Failed to read initial voltage for servo {servo_to_add_id}: {voltage_error}")

            # Broadcast the servo's addition or status update
            broadcast_servo_status(node, servo_to_add_id, servos)
            # We'll broadcast the full list at the end


        # --- Check for Disconnected Servos ---
        # Servos previously known but not in the latest discovery scan
        disconnected_ids = previously_known_servos - discovered_ids
        if disconnected_ids:
            print(f"Servos disconnected: {disconnected_ids}")
            for servo_id in disconnected_ids:
                if servo_id in servos:
                    del servos[servo_id]
                    # Optionally broadcast a removal message here if needed
                    # broadcast_servo_removed(node, servo_id)

        # --- Update Voltage for All Currently Connected Servos ---
        # Iterate over a copy of keys in case of errors during read causing removal elsewhere
        active_servo_ids = list(servos.keys())
        for servo_id in active_servo_ids:
             if servo_id in servos: # Check if still present
                 try:
                     servos[servo_id].read_voltage()
                 except Exception as voltage_error:
                     print(f"Warning: Failed to read voltage for servo {servo_id}: {voltage_error}")
                     # Consider removing the servo if voltage read fails consistently
                     # del servos[servo_id]
                     # print(f"Removed servo {servo_id} due to voltage read failure.")

        # --- Broadcast the final list of *currently responsive* servos ---
        # Only log when there's a change in servo list
        if set(servos.keys()) != previously_known_servos:
            print(f"Broadcasting updated servos list: {list(servos.keys())}")
        broadcast_servos_list(node, servos)

    except Exception as e:
        print(f"Error during scan_for_servos: {e}")
        traceback.print_exc()