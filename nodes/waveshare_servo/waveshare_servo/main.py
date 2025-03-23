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
import os
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
        # Try by direct name first (this was used in the previous implementation)
        try:
            device_path = '/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FD016638-if00'
            if os.path.exists(device_path):
                print(f"Found servo controller at {device_path}")
                return device_path
        except Exception as e:
            print(f"Error checking direct device path: {e}")
        
        # Fall back to scanning ports
        try:
            ports = list(serial.tools.list_ports.comports())
            for port in ports:
                # Check for typical USB-Serial device identifiers
                if any(id_str in port.description for id_str in 
                      ["USB-Serial", "CP210", "CH340", "FTDI"]):
                    print(f"Found servo controller at {port.device}")
                    return port.device
        except Exception as e:
            print(f"Error scanning serial ports: {e}")
            
        print("No servo controller found by name or USB identifiers")
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

            # Use the same baud rate as the previous implementation (1000000)
            self.serial_conn = serial.Serial(self.port, 1000000, timeout=0.5)
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

        # Checking for connected servos
        print(f"Scanning for servos...")
        discovered_servos = set()
        
        # Only try SCS protocol format as it was used in previous implementation
        for id in range(1, 16):  # Limit to likely servo IDs (1-15)
            try:
                # SCS protocol format for ping (based on previous implementation)
                cmd = bytearray([0xFF, 0xFF, id, 2, 1])
                checksum = (~sum(cmd[2:]) & 0xFF)
                cmd.append(checksum)
                
                # Send quietly without logging every attempt
                self.serial_conn.write(cmd)
                self.serial_conn.flush()
                time.sleep(0.05)  # Short wait for response
                response = self.serial_conn.read(self.serial_conn.in_waiting)
                
                # Check response
                if response and len(response) > 0:
                    discovered_servos.add(id)
            except Exception as e:
                print(f"Error while pinging servo {id}: {e}")

        # Only print results at the end
        if discovered_servos:
            print(f"Found servos with IDs: {discovered_servos}")
        else:
            print("No servos found")
            
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
            # Use SCS protocol format for most commands (based on previous implementation)
            if command == "PING":
                # Ping command
                cmd = bytearray([0xFF, 0xFF, self.id, 2, 1])
                checksum = (~sum(cmd[2:]) & 0xFF)
                cmd.append(checksum)
                self.serial_conn.write(cmd)
                self.serial_conn.flush()
                time.sleep(0.05)
                binary_response = self.serial_conn.read(self.serial_conn.in_waiting)
                if binary_response:
                    return "OK"
            elif command.startswith("P") and "T" in command:
                # Position command with time: P<position>T<time>
                # Parse position and time values
                try:
                    position_str = command[1:command.index("T")]
                    time_str = command[command.index("T")+1:]
                    position = int(position_str)
                    time_value = int(time_str)
                    
                    # Send as SCS format
                    # Write Goal Position (address 42) for SCS servo
                    addr = 42  # Position address
                    cmd = bytearray([0xFF, 0xFF, self.id, 5, 3, addr, position & 0xFF, (position >> 8) & 0xFF])
                    checksum = (~sum(cmd[2:]) & 0xFF)
                    cmd.append(checksum)
                    self.serial_conn.write(cmd)
                    self.serial_conn.flush()
                    time.sleep(0.05)
                    # Also set speed if specified
                    if time_value > 0:
                        addr = 46  # Speed address
                        cmd = bytearray([0xFF, 0xFF, self.id, 5, 3, addr, time_value & 0xFF, (time_value >> 8) & 0xFF])
                        checksum = (~sum(cmd[2:]) & 0xFF)
                        cmd.append(checksum)
                        self.serial_conn.write(cmd)
                        self.serial_conn.flush()
                    return "OK"
                except Exception as e:
                    print(f"Error parsing position command: {e}")
            elif command.startswith("ID"):
                # Change ID command
                try:
                    new_id = int(command[2:])
                    if 1 <= new_id <= 31:
                        addr = 5  # ID address
                        cmd = bytearray([0xFF, 0xFF, self.id, 4, 3, addr, new_id])
                        checksum = (~sum(cmd[2:]) & 0xFF)
                        cmd.append(checksum)
                        self.serial_conn.write(cmd)
                        self.serial_conn.flush()
                        time.sleep(0.1)
                        return "OK"
                except Exception as e:
                    print(f"Error parsing ID command: {e}")
            else:
                # Fallback to text format for other commands
                full_command = f"#{self.id}{command}\r\n"
                self.serial_conn.write(full_command.encode())
                self.serial_conn.flush()
                time.sleep(0.1)
                response = self.serial_conn.readline().decode().strip()
                return response
                
            return None
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
        try:
            data = json.dumps({"path": path, "value": value})
            self.node.send_output(
                "update_setting", pa.array([data])
            )
        except Exception as e:
            print(f"Error sending update_setting: {e}")
            traceback.print_exc()

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
            
            # No need to log again - scanner already logged the discovered IDs
            
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
        try:
            if servo_id in self.servos:
                servo = self.servos[servo_id]
                self.node.send_output(
                    "servo_status",
                    pa.array([json.dumps(servo.settings.to_dict())])
                )
        except Exception as e:
            print(f"Error broadcasting servo status: {e}")
            traceback.print_exc()

    def broadcast_servos_list(self):
        """Broadcast the list of all servos."""
        try:
            servo_list = [servo.settings.to_dict() for servo in self.servos.values()]
            self.node.send_output(
                "servos_list", 
                pa.array([json.dumps(servo_list)])
            )
        except Exception as e:
            print(f"Error broadcasting servos list: {e}")
            traceback.print_exc()

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
                    # Try to get data either from "data" or "value" field
                    data_field = None
                    if "data" in event and event["data"] is not None:
                        data_field = event["data"]
                    elif "value" in event and event["value"] is not None:
                        data_field = event["value"]
                    
                    if data_field is not None:
                        data_list = data_field.as_py()
                        if data_list and len(data_list) > 0:
                            data = json.loads(data_list[0])
                            servo_id = data.get("id")
                            position = data.get("position")
                            if servo_id is not None and position is not None:
                                self.handle_move_servo(servo_id, position)
                except Exception as e:
                    print(f"Error processing move_servo event: {e}")
                    traceback.print_exc()
            
            elif event_id == "wiggle_servo":
                try:
                    # Try to get data either from "data" or "value" field
                    data_field = None
                    if "data" in event and event["data"] is not None:
                        data_field = event["data"]
                    elif "value" in event and event["value"] is not None:
                        data_field = event["value"]
                    
                    if data_field is not None:
                        data_list = data_field.as_py()
                        if data_list and len(data_list) > 0:
                            data = json.loads(data_list[0])
                            servo_id = data.get("id")
                            if servo_id is not None:
                                self.handle_wiggle_servo(servo_id)
                except Exception as e:
                    print(f"Error processing wiggle_servo event: {e}")
                    traceback.print_exc()
            
            elif event_id == "calibrate_servo":
                try:
                    # Try to get data either from "data" or "value" field
                    data_field = None
                    if "data" in event and event["data"] is not None:
                        data_field = event["data"]
                    elif "value" in event and event["value"] is not None:
                        data_field = event["value"]
                    
                    if data_field is not None:
                        data_list = data_field.as_py()
                        if data_list and len(data_list) > 0:
                            data = json.loads(data_list[0])
                            servo_id = data.get("id")
                            if servo_id is not None:
                                self.handle_calibrate_servo(servo_id)
                except Exception as e:
                    print(f"Error processing calibrate_servo event: {e}")
                    traceback.print_exc()
            
            elif event_id == "update_servo_setting":
                try:
                    # Try to get data either from "data" or "value" field
                    data_field = None
                    if "data" in event and event["data"] is not None:
                        data_field = event["data"]
                    elif "value" in event and event["value"] is not None:
                        data_field = event["value"]
                    
                    if data_field is not None:
                        data_list = data_field.as_py()
                        if data_list and len(data_list) > 0:
                            data = json.loads(data_list[0])
                            servo_id = data.get("id")
                            property_name = data.get("property")
                            value = data.get("value")
                            if all(x is not None for x in [servo_id, property_name, value]):
                                self.handle_update_servo_setting(servo_id, property_name, value)
                except Exception as e:
                    print(f"Error processing update_servo_setting event: {e}")
                    traceback.print_exc()
            
            elif event_id == "tick":
                try:
                    self.scan_for_servos()
                except Exception as e:
                    print(f"Error processing tick event: {e}")
            
            elif event_id == "settings":
                try:
                    # Periodic settings broadcast from config node
                    # This is a complex field - we need to try different methods to extract data
                    
                    # First try: if it's a StructArray or other arrow type
                    try:
                        if "data" in event and event["data"] is not None:
                            # Try to convert the arrow array to a dict directly
                            if hasattr(event["data"], "to_pylist"):
                                settings_list = event["data"].to_pylist()
                                if settings_list and len(settings_list) > 0:
                                    data = settings_list[0] 
                                    
                                    # Process the data if it's a dict
                                    if isinstance(data, dict):
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
                        print(f"Error parsing primary settings format: {e}")
                        
                    # If that didn't work, try alternative methods
                    # This is a fallback for settings event structures
                    if "value" in event and event["value"] is not None:
                        try:
                            alt_data = None  # Initialize the variable properly
                            
                            # Try direct conversion if value is already a dict
                            if isinstance(event["value"], dict):
                                alt_data = event["value"]
                            elif hasattr(event["value"], "to_pylist"):
                                value_list = event["value"].to_pylist()
                                if value_list and len(value_list) > 0:
                                    alt_data = value_list[0]
                                    if isinstance(alt_data, str):
                                        # Try to parse as JSON if it's a string
                                        alt_data = json.loads(alt_data)
                                    
                            # Process settings data (if found)
                            if alt_data and isinstance(alt_data, dict):
                                for key, value in alt_data.items():
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
                            print(f"Error parsing alternative settings format: {e}")
                except Exception as e:
                    print(f"Error processing settings event: {e}")
                    # traceback.print_exc()  # Comment out to reduce log noise
            
            elif event_id == "setting_updated":
                try:
                    # Individual setting update from config node
                    path = None
                    value = None
                    
                    # Try various formats to extract data
                    data = None
                    
                    # Try direct data field
                    if "data" in event and event["data"] is not None:
                        try:
                            if hasattr(event["data"], "to_pylist"):
                                data_list = event["data"].to_pylist()
                                if data_list and len(data_list) > 0:
                                    if isinstance(data_list[0], str):
                                        data = json.loads(data_list[0])
                                    else:
                                        data = data_list[0]
                        except Exception as e:
                            print(f"Error parsing setting_updated data field: {e}")
                    
                    # Try value field as backup
                    if data is None and "value" in event and event["value"] is not None:
                        try:
                            if isinstance(event["value"], dict):
                                data = event["value"]
                            elif hasattr(event["value"], "to_pylist"):
                                value_list = event["value"].to_pylist()
                                if value_list and len(value_list) > 0:
                                    if isinstance(value_list[0], str):
                                        data = json.loads(value_list[0])
                                    else:
                                        data = value_list[0]
                        except Exception as e:
                            print(f"Error parsing setting_updated value field: {e}")
                    
                    # Extract path and value from the data
                    if isinstance(data, dict):
                        path = data.get("path", "")
                        value = data.get("value")
                    
                    # Process the setting update if we got valid data
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
                    # traceback.print_exc()  # Comment out to reduce log noise
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