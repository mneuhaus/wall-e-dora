"""
Waveshare Servo Node for WALL-E-DORA project.

This node handles all servo-related operations:
- Servo discovery and ID assignment
- Servo movement and control
- Servo calibration
- Servo settings management via the config node
"""

from dora import Node
import traceback
import json
import time
from dataclasses import asdict, dataclass
from typing import Dict, Optional, Set

import pyarrow as pa
import serial
import serial.tools.list_ports


@dataclass
class ServoSettings:
    """Represents settings for a single servo."""
    id: int
    alias: str = ""
    min_pulse: int = 500
    max_pulse: int = 2500
    speed: int = 1000
    calibrated: bool = False
    position: int = 0
    invert: bool = False

    def to_dict(self) -> dict:
        """Convert settings to dictionary for config/json."""
        return asdict(self)


class ServoScanner:
    """Handles scanning for and identifying connected servos."""

    def __init__(self):
        self.port = None
        self.serial_conn = None

    def find_servo_port(self) -> Optional[str]:
        """Find the serial port for the servo controller."""
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            # Check for typical USB-Serial device identifiers
            if any(id_str in port.description for id_str in 
                  ["USB-Serial", "CP210", "CH340", "FTDI"]):
                return port.device
        return None

    def connect(self) -> bool:
        """Connect to the servo controller."""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                return True

            self.port = self.find_servo_port()
            if not self.port:
                print("No servo controller found")
                return False

            self.serial_conn = serial.Serial(self.port, 115200, timeout=0.5)
            time.sleep(0.1)  # Allow time for connection to establish
            return True
        except Exception as e:
            print(f"Failed to connect to servo controller: {e}")
            return False

    def disconnect(self):
        """Disconnect from the servo controller."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def discover_servos(self) -> Set[int]:
        """Discover all connected servos."""
        if not self.connect():
            return set()

        discovered_servos = set()
        for id in range(1, 32):  # Waveshare servos typically use IDs 1-31
            try:
                self.serial_conn.write(f"#{id}PING\r\n".encode())
                response = self.serial_conn.readline().decode().strip()
                if response and "OK" in response:
                    discovered_servos.add(id)
            except Exception as e:
                print(f"Error while pinging servo {id}: {e}")

        return discovered_servos


class Servo:
    """Represents a single servo with all its operations."""

    def __init__(self, serial_conn, settings: ServoSettings):
        self.serial_conn = serial_conn
        self.settings = settings
        self.id = settings.id

    def send_command(self, command: str) -> Optional[str]:
        """Send a command to the servo and get the response."""
        try:
            full_command = f"#{self.id}{command}\r\n"
            self.serial_conn.write(full_command.encode())
            response = self.serial_conn.readline().decode().strip()
            return response
        except Exception as e:
            print(f"Error sending command to servo {self.id}: {e}")
            return None

    def set_id(self, new_id: int) -> bool:
        """Set a new ID for the servo."""
        if 1 <= new_id <= 31:
            response = self.send_command(f"ID{new_id}")
            if response and "OK" in response:
                self.id = new_id
                self.settings.id = new_id
                return True
        return False

    def wiggle(self) -> bool:
        """Wiggle the servo for identification."""
        try:
            current_pos = self.settings.position
            # Move to slight left and right of current position
            wiggle_range = 100
            for _ in range(2):  # Wiggle twice
                positions = [
                    current_pos - wiggle_range,
                    current_pos,
                    current_pos + wiggle_range,
                    current_pos,
                ]
                for pos in positions:
                    safe_pos = max(
                        self.settings.min_pulse, min(self.settings.max_pulse, pos)
                    )
                    self.move(safe_pos)
                    time.sleep(0.2)
            return True
        except Exception as e:
            print(f"Error wiggling servo {self.id}: {e}")
            return False

    def move(self, position: int) -> bool:
        """Move the servo to a specific position."""
        try:
            safe_position = max(
                self.settings.min_pulse, min(self.settings.max_pulse, position)
            )
            
            # Invert position if needed
            if self.settings.invert:
                safe_position = self.settings.max_pulse - (safe_position - self.settings.min_pulse)
            
            command = f"P{safe_position}T{self.settings.speed}"
            response = self.send_command(command)
            
            if response and "OK" in response:
                self.settings.position = position  # Store the requested position
                return True
            return False
        except Exception as e:
            print(f"Error moving servo {self.id}: {e}")
            return False

    def calibrate(self) -> bool:
        """Calibrate the servo min/max values."""
        try:
            # Test minimum position
            self.send_command(f"P{self.settings.min_pulse}T{self.settings.speed}")
            time.sleep(1)
            min_result = self.send_command("PULSEGET")
            
            # Test maximum position
            self.send_command(f"P{self.settings.max_pulse}T{self.settings.speed}")
            time.sleep(1)
            max_result = self.send_command("PULSEGET")
            
            if min_result and max_result:
                self.settings.calibrated = True
                return True
            return False
        except Exception as e:
            print(f"Error calibrating servo {self.id}: {e}")
            return False


class ConfigHandler:
    """Handles interaction with the config node."""

    def __init__(self, node):
        self.node = node
        self.cached_settings = {}
        self.config_prefix = "servo"

    def get_servo_path(self, servo_id: int, property_name: Optional[str] = None) -> str:
        """Get the config path for a servo property."""
        base_path = f"{self.config_prefix}.{servo_id}"
        if property_name:
            return f"{base_path}.{property_name}"
        return base_path

    def update_setting(self, path: str, value: any):
        """Update a setting in the config node."""
        self.node.send_output(
            "update_setting", pa.array([json.dumps({"path": path, "value": value})])
        )

    def update_servo_setting(self, servo_id: int, property_name: str, value: any):
        """Update a specific servo setting."""
        path = self.get_servo_path(servo_id, property_name)
        self.update_setting(path, value)
        
        # Also update local cache
        if servo_id not in self.cached_settings:
            self.cached_settings[servo_id] = {}
        self.cached_settings[servo_id][property_name] = value

    def update_servo_settings(self, settings: ServoSettings):
        """Update all settings for a servo."""
        servo_id = settings.id
        servo_dict = settings.to_dict()
        
        # Update each property individually
        for prop, value in servo_dict.items():
            self.update_servo_setting(servo_id, prop, value)

    def get_servo_settings(self, servo_id: int) -> Optional[dict]:
        """Get settings for a specific servo from cache."""
        return self.cached_settings.get(servo_id, {})

    def handle_settings_updated(self, setting_path: str, new_value: any):
        """Handle a setting update from the config node."""
        # Check if this is a servo setting
        parts = setting_path.split(".")
        if len(parts) >= 2 and parts[0] == self.config_prefix:
            try:
                servo_id = int(parts[1])
                
                # Make sure we have a dict for this servo
                if servo_id not in self.cached_settings:
                    self.cached_settings[servo_id] = {}
                
                # Handle full servo settings update vs. single property update
                if len(parts) == 2:
                    # Full servo settings object
                    self.cached_settings[servo_id] = new_value
                elif len(parts) >= 3:
                    # Single property update
                    property_name = parts[2]
                    self.cached_settings[servo_id][property_name] = new_value
                
                return True
            except (ValueError, IndexError):
                print(f"Invalid servo setting path: {setting_path}")
        
        return False


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
            
            print(f"Discovered servos with IDs: {discovered_ids}")
            
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
                    self.broadcast_servo_status(servo_id)
            
            # Broadcast a complete list of servos
            self.broadcast_servos_list()
            
        except Exception as e:
            print(f"Error scanning for servos: {e}")

    def broadcast_servo_status(self, servo_id: int):
        """Broadcast the status of a single servo."""
        if servo_id in self.servos:
            servo = self.servos[servo_id]
            self.node.send_output(
                "servo_status",
                pa.array([json.dumps(servo.settings.to_dict())])
            )

    def broadcast_servos_list(self):
        """Broadcast the list of all servos."""
        servo_list = [servo.settings.to_dict() for servo in self.servos.values()]
        self.node.send_output(
            "servos_list", 
            pa.array([json.dumps(servo_list)])
        )

    def handle_move_servo(self, servo_id: int, position: int):
        """Handle request to move a servo."""
        if servo_id in self.servos:
            servo = self.servos[servo_id]
            if servo.move(position):
                # Update position in config
                self.config.update_servo_setting(servo_id, "position", position)
                self.broadcast_servo_status(servo_id)
                return True
        return False

    def handle_wiggle_servo(self, servo_id: int):
        """Handle request to wiggle a servo for identification."""
        if servo_id in self.servos:
            servo = self.servos[servo_id]
            return servo.wiggle()
        return False

    def handle_calibrate_servo(self, servo_id: int):
        """Handle request to calibrate a servo."""
        if servo_id in self.servos:
            servo = self.servos[servo_id]
            if servo.calibrate():
                # Update calibration status in config
                self.config.update_servo_setting(servo_id, "calibrated", True)
                self.broadcast_servo_status(servo_id)
                return True
        return False

    def handle_update_servo_setting(self, servo_id: int, property_name: str, value: any):
        """Handle a request to update a servo setting."""
        if servo_id in self.servos:
            servo = self.servos[servo_id]
            
            # Update the setting in the servo object
            if hasattr(servo.settings, property_name):
                setattr(servo.settings, property_name, value)
                
                # Special handling for some properties
                if property_name == "invert" and value:
                    # Recalculate position for inverted servo
                    current_pos = servo.settings.position
                    inverted_pos = servo.settings.max_pulse - (current_pos - servo.settings.min_pulse)
                    servo.settings.position = inverted_pos
                
                # Update config node
                self.config.update_servo_setting(servo_id, property_name, value)
                
                # Broadcast updated status
                self.broadcast_servo_status(servo_id)
                return True
        return False

    def process_event(self, event):
        """Process an incoming event."""
        try:
            if event["type"] != "INPUT":
                return
                
            event_id = event["id"]
            
            if event_id == "move_servo":
                try:
                    data = json.loads(event["data"].as_py()[0])
                    servo_id = data.get("id")
                    position = data.get("position")
                    if servo_id is not None and position is not None:
                        self.handle_move_servo(servo_id, position)
                except Exception as e:
                    print(f"Error processing move_servo event: {e}")
            
            elif event_id == "wiggle_servo":
                try:
                    data = json.loads(event["data"].as_py()[0])
                    servo_id = data.get("id")
                    if servo_id is not None:
                        self.handle_wiggle_servo(servo_id)
                except Exception as e:
                    print(f"Error processing wiggle_servo event: {e}")
            
            elif event_id == "calibrate_servo":
                try:
                    data = json.loads(event["data"].as_py()[0])
                    servo_id = data.get("id")
                    if servo_id is not None:
                        self.handle_calibrate_servo(servo_id)
                except Exception as e:
                    print(f"Error processing calibrate_servo event: {e}")
            
            elif event_id == "update_servo_setting":
                try:
                    data = json.loads(event["data"].as_py()[0])
                    servo_id = data.get("id")
                    property_name = data.get("property")
                    value = data.get("value")
                    if all(x is not None for x in [servo_id, property_name, value]):
                        self.handle_update_servo_setting(servo_id, property_name, value)
                except Exception as e:
                    print(f"Error processing update_servo_setting event: {e}")
            
            elif event_id == "tick":
                try:
                    self.scan_for_servos()
                except Exception as e:
                    print(f"Error processing tick event: {e}")
            
            elif event_id == "settings":
                try:
                    # Periodic settings broadcast from config node
                    # Update our cache with the latest settings
                    data = json.loads(event["data"].as_py()[0])
                    
                    # Extract servo settings
                    for key, value in data.items():
                        parts = key.split(".")
                        if len(parts) >= 2 and parts[0] == "servo":
                            try:
                                servo_id = int(parts[1])
                                if len(parts) == 2:
                                    # Full servo settings
                                    self.config.cached_settings[servo_id] = value
                                elif len(parts) >= 3:
                                    # Individual property
                                    property_name = parts[2]
                                    if servo_id not in self.config.cached_settings:
                                        self.config.cached_settings[servo_id] = {}
                                    self.config.cached_settings[servo_id][property_name] = value
                            except (ValueError, IndexError):
                                continue
                except Exception as e:
                    print(f"Error processing settings event: {e}")
            
            elif event_id == "setting_updated":
                try:
                    # Individual setting update from config node
                    data = json.loads(event["data"].as_py()[0])
                    path = data.get("path", "")
                    value = data.get("value")
                    
                    if path and value is not None:
                        self.config.handle_settings_updated(path, value)
                        
                        # Check if this is a servo setting that needs to be applied
                        parts = path.split(".")
                        if len(parts) >= 3 and parts[0] == "servo":
                            try:
                                servo_id = int(parts[1])
                                property_name = parts[2]
                                
                                # Apply the setting if the servo exists
                                if servo_id in self.servos and hasattr(
                                    self.servos[servo_id].settings, property_name
                                ):
                                    setattr(
                                        self.servos[servo_id].settings, property_name, value
                                    )
                                    
                                    # If this is a position update, actually move the servo
                                    if property_name == "position":
                                        self.servos[servo_id].move(value)
                            except (ValueError, IndexError):
                                pass
                except Exception as e:
                    print(f"Error processing setting_updated event: {e}")
        except Exception as e:
            print(f"Error processing event {event.get('id', 'unknown')}: {e}")


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