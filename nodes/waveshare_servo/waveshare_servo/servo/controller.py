"""Provides the Servo class for controlling individual Waveshare servos."""

from typing import Optional
import time

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
from .sdk import (
    PortHandler, 
    PacketHandler, 
    COMM_SUCCESS
)

# Control table addresses for SCS servos
ADDR_SCS_ID = 5
ADDR_SCS_EEPROM_LOCK = 48
ADDR_SCS_TORQUE_ENABLE = 40
ADDR_SCS_GOAL_POSITION = 42
ADDR_SCS_PRESENT_POSITION = 56
ADDR_SCS_MOVING_SPEED = 46
ADDR_SCS_PRESENT_VOLTAGE = 62  # Address for reading current voltage

# EEPROM lock/unlock values
VALUE_UNLOCK_EEPROM = 0
VALUE_LOCK_EEPROM = 1

# Default device settings
BAUDRATE = 1000000
PROTOCOL_END = 1  # Using protocol_end = 1


class Servo:
    """Represents a single Waveshare servo motor and its operations.

    Handles sending commands, moving the servo, calibration, ID changes,
    and reading status like voltage, using both a text-based protocol
    and the underlying Dynamixel SDK for communication.

    Attributes:
        serial_conn: The shared serial connection object.
        settings: A ServoSettings data object holding the servo's configuration.
        id: The numerical ID of the servo.
    """

    def __init__(self, serial_conn, settings: ServoSettings):
        """Initialize a Servo instance.

        Args:
            serial_conn: The PySerial connection object used for communication.
            settings: A ServoSettings data object containing the initial
                      configuration for this servo.
        """
        self.serial_conn = serial_conn
        self.settings = settings
        self.id = settings.id

    def send_command(self, command: str) -> Optional[str]:
        """Send a command string to the servo and return the response.

        Determines the appropriate protocol (SCS binary or text-based) based
        on the command format and sends it via the serial connection.

        Args:
            command: The command string to send (e.g., "PING", "P1500T1000", "ID2").

        Returns:
            The response string from the servo, or None if an error occurred.
        """
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

    def is_responsive(self) -> bool:
        """Check if the servo is responsive by sending a PING command using the SDK.

        Returns:
            True if the servo responds successfully to the ping, False otherwise.
        """
        device_name = self.serial_conn.port
        port_handler = None
        
        try:
            # Initialize SDK components
            port_handler = PortHandler(device_name)
            packet_handler = PacketHandler(PROTOCOL_END)
            
            # Open port
            if not port_handler.openPort():
                return False
                
            if not port_handler.setBaudRate(BAUDRATE):
                port_handler.closePort()
                return False
                
            # Ping the servo
            model_num, result, error = packet_handler.ping(port_handler, self.id)
            
            # Clean up
            port_handler.closePort()
            
            # Return result
            return result == COMM_SUCCESS and error == 0
            
        except Exception as e:
            if port_handler and port_handler.isOpen():
                port_handler.closePort()
            return False

    def set_id(self, new_id: int) -> bool:
        """Set a new ID for the servo using the SDK.

        Handles unlocking the EEPROM, writing the new ID, and re-locking the
        EEPROM with the new ID. Updates the servo object's ID upon success.

        Args:
            new_id: The new ID to assign (must be between 1 and 31).

        Returns:
            True if the ID change was successful, False otherwise.
        """
        if not (1 <= new_id <= 31):
            print(f"Invalid servo ID {new_id}. Must be between 1 and 31.")
            return False
            
        # Use only SDK approach
        return self._set_id_with_sdk(new_id)

    def _set_id_with_sdk(self, new_id: int) -> bool:
        """Internal helper to set servo ID using the SDK.

        Handles EEPROM lock/unlock and writing the new ID.

        Args:
            new_id: The new ID to assign.

        Returns:
            True on success, False on failure.
        """
        old_id = self.id
        device_name = self.serial_conn.port
        port_handler = None
        
        try:
            # Initialize SDK components
            port_handler = PortHandler(device_name)
            packet_handler = PacketHandler(PROTOCOL_END)
            
            # Open port
            if not port_handler.openPort():
                print(f"Failed to open port for servo {old_id}")
                return False
                
            if not port_handler.setBaudRate(BAUDRATE):
                print(f"Failed to set baudrate for servo {old_id}")
                port_handler.closePort()
                return False
            
            # STEP 1: Unlock EEPROM
            print(f"Unlocking EEPROM for ID {old_id}...")
            result, error = packet_handler.write1ByteTxRx(
                port_handler, old_id, ADDR_SCS_EEPROM_LOCK, VALUE_UNLOCK_EEPROM
            )
            
            if result != COMM_SUCCESS or error != 0:
                print(f"Failed to unlock EEPROM for servo {old_id}")
                print(f"  - Result: {packet_handler.getTxRxResult(result)}")
                if error != 0:
                    print(f"  - Error: {packet_handler.getRxPacketError(error)}")
                port_handler.closePort()
                return False
            
            time.sleep(0.02)  # Small delay after unlock
            
            # STEP 2: Write new ID to the servo
            print(f"Writing new ID {new_id} for servo {old_id}...")
            id_result, id_error = packet_handler.write1ByteTxRx(
                port_handler, old_id, ADDR_SCS_ID, new_id
            )
            
            if id_result != COMM_SUCCESS or id_error != 0:
                print(f"Failed to set new ID {new_id} for servo {old_id}")
                print(f"  - Result: {packet_handler.getTxRxResult(id_result)}")
                if id_error != 0:
                    print(f"  - Error: {packet_handler.getRxPacketError(id_error)}")
                
                # Try to re-lock EEPROM with old ID if ID change fails
                print(f"Attempting safety re-lock with old ID {old_id}...")
                lock_result, lock_error = packet_handler.write1ByteTxRx(
                    port_handler, old_id, ADDR_SCS_EEPROM_LOCK, VALUE_LOCK_EEPROM
                )
                if lock_result != COMM_SUCCESS or lock_error != 0:
                    print("Warning: Safety re-lock failed!")
                
                port_handler.closePort()
                return False
            
            time.sleep(0.1)  # Longer delay for EEPROM write
            
            # STEP 3: Lock EEPROM with NEW ID
            print(f"Locking EEPROM for new ID {new_id}...")
            lock_result, lock_error = packet_handler.write1ByteTxRx(
                port_handler, new_id, ADDR_SCS_EEPROM_LOCK, VALUE_LOCK_EEPROM
            )
            
            if lock_result != COMM_SUCCESS or lock_error != 0:
                print(f"Warning: Failed to lock EEPROM for new ID {new_id}")
                print(f"  - Result: {packet_handler.getTxRxResult(lock_result)}")
                if lock_error != 0:
                    print(f"  - Error: {packet_handler.getRxPacketError(lock_error)}")
                print(f"ID likely changed, but EEPROM remains unlocked.")
            else:
                print(f"EEPROM locked successfully for new ID {new_id}")
            
            # Update the servo object's ID attributes
            self.id = new_id
            self.settings.id = new_id
            
            # Clean up
            port_handler.closePort()
            print(f"Successfully changed servo ID from {old_id} to {new_id}")
            return True
            
        except Exception as e:
            print(f"SDK ID change error for servo {old_id}: {e}")
            if port_handler and port_handler.isOpen():
                port_handler.closePort()
            return False

    def wiggle(self) -> bool:
        """Wiggle the servo slightly for physical identification."""
        return wiggle_servo(self)

    def move(self, position: int) -> bool:
        """Move the servo to a specific target position using the SDK.

        Clamps the position based on the servo's min/max pulse settings and
        applies inversion if configured.

        Args:
            position: The target position value (typically 0-1023).

        Returns:
            True if the move command was sent successfully, False otherwise.
        """
        try:
            # Apply min/max constraints
            safe_position = max(
                self.settings.min_pulse, min(self.settings.max_pulse, position)
            )
            
            # Invert position if needed
            if self.settings.invert:
                safe_position = self.settings.max_pulse - (safe_position - self.settings.min_pulse)
            
            # Use only the SDK-based approach
            return self._move_with_sdk(safe_position)
                
        except Exception as e:
            print(f"Error moving servo {self.id}: {e}")
            return False

    def _move_with_sdk(self, position: int) -> bool:
        """Internal helper to move the servo using the SDK.

        Sends commands to set the speed and then the goal position.

        Args:
            position: The target position value (already clamped and inverted).

        Returns:
            True on success, False on failure.
        """
        # Ensure position is within the valid range (0-1023)
        position = max(0, min(1023, position))
        
        servo_id = self.id
        device_name = self.serial_conn.port
        port_handler = None
        
        try:
            # Initialize SDK components
            port_handler = PortHandler(device_name)
            packet_handler = PacketHandler(PROTOCOL_END)
            
            # Open port
            if not port_handler.openPort():
                print(f"Failed to open port for servo {servo_id}")
                return False
                
            if not port_handler.setBaudRate(BAUDRATE):
                print(f"Failed to set baudrate for servo {servo_id}")
                port_handler.closePort()
                return False
            
            # Set the speed first if it's not zero
            if self.settings.speed > 0:
                speed_result, speed_error = packet_handler.write2ByteTxRx(
                    port_handler, servo_id, ADDR_SCS_MOVING_SPEED, self.settings.speed
                )
                
                if speed_result != COMM_SUCCESS or speed_error != 0:
                    print(f"Warning: Failed to set speed for servo {servo_id}")
                    # Continue anyway as position is more important
            
            # Now set the position
            pos_result, pos_error = packet_handler.write2ByteTxRx(
                port_handler, servo_id, ADDR_SCS_GOAL_POSITION, position
            )
            
            if pos_result != COMM_SUCCESS or pos_error != 0:
                print(f"Failed to set position {position} for servo {servo_id}")
                print(f"  - Result: {packet_handler.getTxRxResult(pos_result)}")
                if pos_error != 0:
                    print(f"  - Error: {packet_handler.getRxPacketError(pos_error)}")
                port_handler.closePort()
                return False
            
            # Store position in settings for reference
            self.settings.position = position
            
            # Clean up
            port_handler.closePort()
            return True
            
        except Exception as e:
            print(f"SDK move error for servo {servo_id}: {e}")
            if port_handler and port_handler.isOpen():
                port_handler.closePort()
            return False

    def calibrate(self) -> bool:
        """Initiate the servo calibration process."""
        return calibrate_servo(self)

    def read_voltage(self) -> float:
        """Read the current voltage from the servo using the SDK.

        Updates the `self.settings.voltage` attribute.

        Returns:
            The current voltage in volts, or 0.0 if the read fails.
        """
        device_name = self.serial_conn.port
        port_handler = None
        
        try:
            # Initialize SDK components
            port_handler = PortHandler(device_name)
            packet_handler = PacketHandler(PROTOCOL_END)
            
            # Open port
            if not port_handler.openPort():
                print(f"Failed to open port for servo {self.id}")
                return 0.0
                
            if not port_handler.setBaudRate(BAUDRATE):
                print(f"Failed to set baudrate for servo {self.id}")
                port_handler.closePort()
                return 0.0
            
            # Read voltage (1 byte)
            voltage_raw, result, error = packet_handler.read1ByteTxRx(
                port_handler, self.id, ADDR_SCS_PRESENT_VOLTAGE
            )
            
            if result != COMM_SUCCESS or error != 0:
                print(f"Failed to read voltage from servo {self.id}")
                port_handler.closePort()
                return 0.0
            
            # Convert raw voltage to actual voltage
            # Most servos use a factor of 10 (e.g., a value of 120 means 12.0V)
            voltage = voltage_raw / 10.0
            
            # Update the servo settings
            self.settings.voltage = voltage
            
            # Clean up
            port_handler.closePort()
            return voltage
            
        except Exception as e:
            print(f"Error reading voltage from servo {self.id}: {e}")
            if port_handler and port_handler.isOpen():
                port_handler.closePort()
            return 0.0
