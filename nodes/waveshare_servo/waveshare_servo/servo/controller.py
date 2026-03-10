"""Provides the Servo class for controlling individual Waveshare servos."""

from typing import Optional
import time

from .models import ServoSettings
from .wiggle import wiggle_servo
from .calibrate import calibrate_servo
from .sdk import COMM_SUCCESS

# Control table addresses for SCS servos
ADDR_SCS_ID = 5
ADDR_SCS_EEPROM_LOCK = 48
ADDR_SCS_TORQUE_ENABLE = 40
ADDR_SCS_GOAL_POSITION = 42
ADDR_SCS_PRESENT_POSITION = 56
ADDR_SCS_MOVING_SPEED = 46
ADDR_SCS_PRESENT_VOLTAGE = 62

# EEPROM lock/unlock values
VALUE_UNLOCK_EEPROM = 0
VALUE_LOCK_EEPROM = 1


class Servo:
    """Represents a single Waveshare servo motor and its operations.

    Uses a shared PortHandler and PacketHandler for all communication,
    avoiding multiple serial connections to the same port.

    Attributes:
        port_handler: The shared SDK PortHandler instance.
        packet_handler: The shared SDK PacketHandler instance.
        settings: A ServoSettings data object holding the servo's configuration.
        id: The numerical ID of the servo.
    """

    def __init__(self, port_handler, packet_handler, settings: ServoSettings):
        """Initialize a Servo instance.

        Args:
            port_handler: The shared SDK PortHandler instance.
            packet_handler: The shared SDK PacketHandler instance.
            settings: A ServoSettings data object containing the initial
                      configuration for this servo.
        """
        self.port_handler = port_handler
        self.packet_handler = packet_handler
        self.settings = settings
        self.id = settings.id

    @property
    def serial_conn(self):
        """Backward-compatible access to the underlying serial connection."""
        return self.port_handler.ser if self.port_handler else None

    def is_responsive(self) -> bool:
        """Check if the servo is responsive by sending a PING command.

        Returns:
            True if the servo responds successfully to the ping, False otherwise.
        """
        try:
            model_num, result, error = self.packet_handler.ping(
                self.port_handler, self.id
            )
            return result == COMM_SUCCESS and error == 0
        except Exception as e:
            return False

    def set_id(self, new_id: int) -> bool:
        """Set a new ID for the servo using the SDK.

        Args:
            new_id: The new ID to assign (must be between 1 and 31).

        Returns:
            True if the ID change was successful, False otherwise.
        """
        if not (1 <= new_id <= 31):
            print(f"Invalid servo ID {new_id}. Must be between 1 and 31.")
            return False

        old_id = self.id
        ph = self.port_handler
        pkt = self.packet_handler

        try:
            # STEP 1: Unlock EEPROM
            print(f"Unlocking EEPROM for ID {old_id}...")
            result, error = pkt.write1ByteTxRx(
                ph, old_id, ADDR_SCS_EEPROM_LOCK, VALUE_UNLOCK_EEPROM
            )
            if result != COMM_SUCCESS or error != 0:
                print(f"Failed to unlock EEPROM for servo {old_id}")
                return False

            time.sleep(0.02)

            # STEP 2: Write new ID
            print(f"Writing new ID {new_id} for servo {old_id}...")
            id_result, id_error = pkt.write1ByteTxRx(
                ph, old_id, ADDR_SCS_ID, new_id
            )
            if id_result != COMM_SUCCESS or id_error != 0:
                print(f"Failed to set new ID {new_id} for servo {old_id}")
                # Try to re-lock EEPROM with old ID
                pkt.write1ByteTxRx(ph, old_id, ADDR_SCS_EEPROM_LOCK, VALUE_LOCK_EEPROM)
                return False

            time.sleep(0.1)

            # STEP 3: Lock EEPROM with NEW ID
            print(f"Locking EEPROM for new ID {new_id}...")
            lock_result, lock_error = pkt.write1ByteTxRx(
                ph, new_id, ADDR_SCS_EEPROM_LOCK, VALUE_LOCK_EEPROM
            )
            if lock_result != COMM_SUCCESS or lock_error != 0:
                print(f"Warning: Failed to lock EEPROM for new ID {new_id}")

            self.id = new_id
            self.settings.id = new_id
            print(f"Successfully changed servo ID from {old_id} to {new_id}")
            return True

        except Exception as e:
            print(f"SDK ID change error for servo {old_id}: {e}")
            return False

    def wiggle(self) -> bool:
        """Wiggle the servo slightly for physical identification."""
        return wiggle_servo(self)

    def move(self, position: int) -> bool:
        """Move the servo to a specific target position.

        Args:
            position: The target position value (typically 0-1023).

        Returns:
            True if the move command was sent successfully, False otherwise.
        """
        try:
            safe_position = max(
                self.settings.min_pulse, min(self.settings.max_pulse, position)
            )
            if self.settings.invert:
                safe_position = self.settings.max_pulse - (safe_position - self.settings.min_pulse)

            safe_position = max(0, min(1023, safe_position))

            ph = self.port_handler
            pkt = self.packet_handler

            # Reset is_using in case it got stuck
            ph.is_using = False

            # Set speed first if configured
            if self.settings.speed > 0:
                pkt.write2ByteTxRx(
                    ph, self.id, ADDR_SCS_MOVING_SPEED, self.settings.speed
                )

            # Set position
            pos_result, pos_error = pkt.write2ByteTxRx(
                ph, self.id, ADDR_SCS_GOAL_POSITION, safe_position
            )
            if pos_result != COMM_SUCCESS or pos_error != 0:
                print(f"Failed to set position {safe_position} for servo {self.id}")
                return False

            self.settings.position = safe_position
            return True

        except Exception as e:
            print(f"Error moving servo {self.id}: {e}")
            return False

    def calibrate(self) -> bool:
        """Initiate the servo calibration process."""
        return calibrate_servo(self)

    def read_voltage(self) -> float:
        """Read the current voltage from the servo.

        Returns:
            The current voltage in volts, or 0.0 if the read fails.
        """
        try:
            # Reset state and flush buffer before reading
            self.port_handler.is_using = False
            try:
                self.port_handler.ser.reset_input_buffer()
            except Exception:
                pass
            voltage_raw, result, error = self.packet_handler.read1ByteTxRx(
                self.port_handler, self.id, ADDR_SCS_PRESENT_VOLTAGE
            )
            if result != COMM_SUCCESS or error != 0:
                print(f"Failed to read voltage from servo {self.id}")
                return 0.0

            voltage = voltage_raw / 10.0
            self.settings.voltage = voltage
            return voltage

        except Exception as e:
            print(f"Error reading voltage from servo {self.id}: {e}")
            return 0.0

    def send_command(self, command: str) -> Optional[str]:
        """Send a command string to the servo.

        Args:
            command: The command string (e.g., "PING", "P1500T1000").

        Returns:
            The response string, or None if an error occurred.
        """
        try:
            if not command or not isinstance(command, str):
                return None

            if command == "PING":
                model_num, result, error = self.packet_handler.ping(
                    self.port_handler, self.id
                )
                return "OK" if result == COMM_SUCCESS else None

            elif command.startswith("P"):
                if len(command) == 1:
                    return "OK"
                elif "T" in command:
                    try:
                        parts = command[1:].split("T")
                        position = int(parts[0])
                        time_value = int(parts[1])
                        # Use move for position commands
                        old_speed = self.settings.speed
                        self.settings.speed = time_value
                        result = self.move(position)
                        self.settings.speed = old_speed
                        return "OK" if result else None
                    except Exception as e:
                        print(f"Error parsing position command '{command}': {e}")
                        return None

            elif command.startswith("ID"):
                try:
                    new_id = int(command[2:])
                    return "OK" if self.set_id(new_id) else None
                except Exception as e:
                    print(f"Error parsing ID command '{command}': {e}")
                    return None

            return None
        except Exception as e:
            print(f"Error sending command to servo {self.id}: {e}")
            return None
