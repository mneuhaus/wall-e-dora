"""
Waveshare Servo Node for WALL-E-DORA project.

This node handles all servo-related operations:
- Servo discovery and ID assignment
- Servo movement and control
- Servo calibration
- Servo settings management via the config node
"""

import traceback
import sys
import os
from typing import Dict

# Add the current directory to the path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from dora import Node
from servo import Servo, ServoSettings, ServoScanner
from config_handler import ConfigHandler
from outputs import broadcast_servo_status, broadcast_servos_list
from inputs import (
    handle_move_servo, 
    handle_wiggle_servo, 
    handle_calibrate_servo,
    handle_update_servo_setting,
    handle_tick, 
    handle_settings,
    handle_setting_updated
)


class ServoManager:
    """Main class that manages all servo operations."""

    def __init__(self, node):
        self.node = node
        self.scanner = ServoScanner()
        self.config = ConfigHandler(node)
        self.servos: Dict[int, Servo] = {}
        self.next_available_id = 2  # Reserved IDs start from 2

    def initialize(self):
        """Initialize the servo manager."""
        try:
            if self.scanner.connect():
                self.scan_for_servos()
            else:
                print("Failed to connect to servo controller - will retry on next tick")
        except Exception as e:
            print(f"Error initializing servo manager: {e}")
            # Continue running even without a servo controller

    def scan_for_servos(self):
        """Scan for servos and initialize them."""
        try:
            discovered_ids = self.scanner.discover_servos()
            
            for servo_id in discovered_ids:
                if servo_id not in self.servos:
                    # Get settings from config or use defaults
                    settings_dict = self.config.get_servo_settings(servo_id)
                    
                    # Create default settings if not found
                    if not settings_dict:
                        settings = ServoSettings(id=servo_id)
                        
                        # If this is the default ID (1), assign a new unique ID
                        if servo_id == 1:
                            new_id = self.next_available_id
                            self.next_available_id += 1
                            
                            # Create servo temporarily with ID 1
                            temp_servo = Servo(self.scanner.serial_conn, settings)
                            
                            # Attempt to change the ID
                            if temp_servo.set_id(new_id):
                                # Update the settings with the new ID
                                settings.id = new_id
                                servo_id = new_id
                            else:
                                print(f"Failed to assign new ID to servo {servo_id}")
                        
                        # Save the settings to config
                        self.config.update_servo_settings(settings)
                    else:
                        # Convert dict to ServoSettings
                        settings = ServoSettings(**settings_dict)
                    
                    # Create and store the servo
                    self.servos[servo_id] = Servo(self.scanner.serial_conn, settings)
                    
                    # Broadcast the servo's addition
                    broadcast_servo_status(self.node, servo_id, self.servos)
            
            # Broadcast a complete list of servos
            broadcast_servos_list(self.node, self.servos)
            
        except Exception as e:
            print(f"Error scanning for servos: {e}")

    def process_event(self, event):
        """Process an incoming event."""
        try:
            if event["type"] != "INPUT":
                return
                
            event_id = event["id"]
            
            # Map event IDs to handler functions
            handlers = {
                "move_servo": lambda evt: handle_move_servo(self, evt),
                "wiggle_servo": lambda evt: handle_wiggle_servo(self, evt),
                "calibrate_servo": lambda evt: handle_calibrate_servo(self, evt),
                "update_servo_setting": lambda evt: handle_update_servo_setting(self, evt),
                "tick": lambda evt: handle_tick(self, evt),
                "settings": lambda evt: handle_settings(self, evt),
                "setting_updated": lambda evt: handle_setting_updated(self, evt)
            }
            
            # Call the appropriate handler if available
            if event_id in handlers:
                handlers[event_id](event)
            
        except Exception as e:
            print(f"Error processing event {event.get('id', 'unknown')}: {e}")
            traceback.print_exc()


def main():
    """Entry point for the node."""
    try:
        node = Node()
        print("Waveshare Servo Node starting...")
        
        # Initialize servo manager
        manager = ServoManager(node)
        manager.initialize()
        
        print("Starting main event loop...")
        # Main event loop
        for event in node:
            try:
                # Process incoming events
                manager.process_event(event)
            except Exception as e:
                print(f"Unexpected error in event loop: {e}")
                traceback.print_exc()
    except Exception as e:
        print(f"Error starting waveshare_servo node: {e}")
        traceback.print_exc()
        # Don't re-raise exception so the process exits gracefully


if __name__ == "__main__":
    main()