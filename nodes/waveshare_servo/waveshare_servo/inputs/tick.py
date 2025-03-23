"""
Handler for tick events.
"""

import traceback
from typing import Dict, Any
import sys
import os

# Add the parent directory to the path for imports if needed
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
        print(f"Error processing tick event: {e}")
        return False


def scan_for_servos(context):
    """Scan for servos and initialize them."""
    try:
        node = context["node"]
        scanner = context["scanner"]
        config = context["config"]
        servos = context["servos"]
        next_available_id = context["next_available_id"]
        
        discovered_ids = scanner.discover_servos()
        
        for servo_id in discovered_ids:
            if servo_id not in servos:
                # Get settings from config or use defaults
                settings_dict = config.get_servo_settings(servo_id)
                
                # Create default settings if not found
                if not settings_dict:
                    settings = ServoSettings(id=servo_id)
                    
                    # If this is the default ID (1), assign a new unique ID
                    if servo_id == 1:
                        new_id = next_available_id
                        next_available_id += 1
                        context["next_available_id"] = next_available_id
                        
                        # Create servo temporarily with ID 1
                        temp_servo = Servo(scanner.serial_conn, settings)
                        
                        # Attempt to change the ID
                        if temp_servo.set_id(new_id):
                            # Update the settings with the new ID
                            settings.id = new_id
                            servo_id = new_id
                        else:
                            print(f"Failed to assign new ID to servo {servo_id}")
                    
                    # Save the settings to config
                    config.update_servo_settings(settings)
                else:
                    # Convert dict to ServoSettings
                    settings = ServoSettings(**settings_dict)
                
                # Create and store the servo
                servos[servo_id] = Servo(scanner.serial_conn, settings)
                
                # Broadcast the servo's addition
                broadcast_servo_status(node, servo_id, servos)
        
        # Broadcast a complete list of servos
        broadcast_servos_list(node, servos)
        
    except Exception as e:
        print(f"Error scanning for servos: {e}")