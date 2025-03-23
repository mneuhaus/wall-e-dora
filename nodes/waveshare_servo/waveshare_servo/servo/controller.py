"""
Individual servo control for the Waveshare Servo Node.
"""

from typing import Optional

# Import from local modules
from .models import ServoSettings
from .protocol import (
    send_ping_command,
    send_position_command,
    parse_position_command,
    send_id_command,
    send_text_command
)
from .wiggle import wiggle_servo
from .calibrate import calibrate_servo


class Servo:
    """Represents a single servo with all its operations."""

    def __init__(self, serial_conn, settings: ServoSettings):
        self.serial_conn = serial_conn
        self.settings = settings
        self.id = settings.id

    def send_command(self, command: str) -> Optional[str]:
        """Send a command to the servo and get the response."""
        try:
            if not command or not isinstance(command, str):
                print(f"Invalid command: {command}")
                return None
                
            # Use SCS protocol format for most commands
            if command == "PING":
                return send_ping_command(self.serial_conn, self.id)
            elif command.startswith("P"):
                # Simple position request with just "P" (for calibration)
                if len(command) == 1:
                    return "OK"  # Just return OK for simple position request
                # Position command with time: P<position>T<time>
                elif "T" in command:
                    try:
                        position, time_value = parse_position_command(command)
                        return send_position_command(self.serial_conn, self.id, position, time_value)
                    except Exception as e:
                        print(f"Error parsing position command '{command}': {e}")
                        return None
                else:
                    print(f"Invalid position command format: {command}")
                    return None
            elif command.startswith("ID"):
                # Change ID command
                try:
                    if len(command) <= 2:
                        print(f"Invalid ID command format: {command}")
                        return None
                        
                    id_str = command[2:]
                    if not id_str.isdigit():
                        print(f"Non-numeric ID in command: {id_str}")
                        return None
                        
                    new_id = int(id_str)
                    return send_id_command(self.serial_conn, self.id, new_id)
                except Exception as e:
                    print(f"Error parsing ID command '{command}': {e}")
                    return None
            else:
                # Fallback to text format for other commands
                print(f"Using text command protocol for: {command}")
                return send_text_command(self.serial_conn, self.id, command)
                
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
        return wiggle_servo(self)

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
        return calibrate_servo(self)