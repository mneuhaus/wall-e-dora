"""Servo controller wrapper around the Waveshare SDK."""

from __future__ import annotations

import time
from typing import Optional

from .diagnostics import read_config, read_model, read_status
from .models import ServoConfig, ServoModel, ServoSettings, ServoStatus
from .operations import auto_calibrate, clone_settings, factory_reset
from .registers import (
    ADDR_EEPROM_LOCK,
    ADDR_GOAL_POSITION,
    ADDR_GOAL_SPEED,
    ADDR_ID,
    ADDR_PRESENT_VOLTAGE,
    EEPROM_LOCKED,
    EEPROM_UNLOCKED,
)
from .sdk import COMM_SUCCESS
from .wiggle import wiggle_servo


class Servo:
    """Represents a single Waveshare servo motor and its operations."""

    def __init__(self, port_handler, packet_handler, settings: ServoSettings):
        self.port_handler = port_handler
        self.packet_handler = packet_handler
        self.settings = settings
        self.id = settings.id

    @property
    def serial_conn(self):
        """Backward-compatible access to the underlying serial connection."""
        return self.port_handler.ser if self.port_handler else None

    def _prepare_port(self) -> None:
        """Reset SDK port state before issuing a new command."""
        self.port_handler.is_using = False
        try:
            if self.port_handler.ser and self.port_handler.ser.is_open:
                self.port_handler.ser.reset_input_buffer()
        except Exception:
            pass

    def is_responsive(self) -> bool:
        """Check if the servo responds to ping."""
        try:
            self._prepare_port()
            _, result, _ = self.packet_handler.ping(self.port_handler, self.id)
            return result == COMM_SUCCESS
        except Exception:
            return False

    def set_id(self, new_id: int) -> bool:
        """Set a new servo ID."""
        if not (1 <= new_id <= 253):
            print(f"Invalid servo ID {new_id}. Must be between 1 and 253.")
            return False

        old_id = self.id
        try:
            self._prepare_port()
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, old_id, ADDR_EEPROM_LOCK, EEPROM_UNLOCKED
            )
            if result != COMM_SUCCESS or error != 0:
                print(f"Failed to unlock EEPROM for servo {old_id}")
                return False

            time.sleep(0.02)
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, old_id, ADDR_ID, new_id
            )
            if result != COMM_SUCCESS or error != 0:
                self.packet_handler.write1ByteTxRx(
                    self.port_handler, old_id, ADDR_EEPROM_LOCK, EEPROM_LOCKED
                )
                print(f"Failed to write ID {new_id} for servo {old_id}")
                return False

            time.sleep(0.05)
            self.packet_handler.write1ByteTxRx(
                self.port_handler, new_id, ADDR_EEPROM_LOCK, EEPROM_LOCKED
            )

            self.id = new_id
            self.settings.id = new_id
            return True
        except Exception as exc:
            print(f"SDK ID change error for servo {old_id}: {exc}")
            return False

    def move(self, position: int) -> bool:
        """Move the servo to a target position."""
        try:
            safe_position = max(self.settings.min_pulse, min(self.settings.max_pulse, position))
            if self.settings.invert:
                safe_position = self.settings.max_pulse - (safe_position - self.settings.min_pulse)
            safe_position = max(0, min(1023, safe_position))

            self._prepare_port()
            if self.settings.speed > 0:
                self.packet_handler.write2ByteTxRx(
                    self.port_handler, self.id, ADDR_GOAL_SPEED, int(self.settings.speed)
                )

            result, error = self.packet_handler.write2ByteTxRx(
                self.port_handler, self.id, ADDR_GOAL_POSITION, safe_position
            )
            if result != COMM_SUCCESS or error != 0:
                print(f"Failed to set position {safe_position} for servo {self.id}")
                return False

            self.settings.position = safe_position
            return True
        except Exception as exc:
            print(f"Error moving servo {self.id}: {exc}")
            return False

    def wiggle(self) -> bool:
        """Wiggle the servo slightly for physical identification."""
        return wiggle_servo(self)

    def calibrate(self) -> bool:
        """Maintain compatibility with older callers."""
        limits = self.auto_calibrate()
        if not limits:
            return False
        self.settings.min_pulse, self.settings.max_pulse = limits
        self.settings.calibrated = True
        return True

    def auto_calibrate(self, step_size: int = 30, load_threshold: int = 300) -> Optional[tuple[int, int]]:
        """Run stall-detection calibration against the physical end stops."""
        return auto_calibrate(
            self.packet_handler,
            self.port_handler,
            self.id,
            step_size=step_size,
            load_threshold=load_threshold,
        )

    def clone_settings_from(self, source_id: int) -> tuple[bool, list[str]]:
        """Clone EEPROM settings from another servo into this one."""
        return clone_settings(self.packet_handler, self.port_handler, source_id, self.id)

    def factory_reset(self) -> tuple[bool, list[str]]:
        """Factory reset this servo back to the default ID and settings."""
        return factory_reset(self.packet_handler, self.port_handler, self.id)

    def read_status(self) -> Optional[ServoStatus]:
        """Read and cache live status telemetry."""
        status = read_status(self.packet_handler, self.port_handler, self.id)
        if status is not None:
            self.settings.position = status.position
            self.settings.voltage = status.voltage
            self.settings.temperature = status.temperature
            self.settings.load = status.load
            self.settings.moving = status.moving
        return status

    def read_model_info(self) -> Optional[ServoModel]:
        """Read and cache the servo model metadata."""
        model = read_model(self.packet_handler, self.port_handler, self.id)
        if model is not None:
            self.settings.model_name = model.name
            self.settings.model_number = model.model_number
        return model

    def read_config(self) -> Optional[ServoConfig]:
        """Read the servo EEPROM and writable SRAM configuration."""
        return read_config(self.packet_handler, self.port_handler, self.id)

    def read_voltage(self) -> float:
        """Read and cache the current servo voltage."""
        status = self.read_status()
        if status is not None:
            return status.voltage

        try:
            self._prepare_port()
            voltage_raw, result, error = self.packet_handler.read1ByteTxRx(
                self.port_handler, self.id, ADDR_PRESENT_VOLTAGE
            )
            if result != COMM_SUCCESS or error != 0:
                return 0.0
            self.settings.voltage = voltage_raw / 10.0
            return self.settings.voltage
        except Exception:
            return 0.0

    def send_command(self, command: str) -> Optional[str]:
        """Compatibility wrapper for older call sites."""
        try:
            if not command or not isinstance(command, str):
                return None

            if command == "PING":
                return "OK" if self.is_responsive() else None

            if command.startswith("P"):
                if len(command) == 1:
                    status = self.read_status()
                    return "OK" if status else None
                if "T" in command:
                    position_str, time_str = command[1:].split("T", 1)
                    old_speed = self.settings.speed
                    self.settings.speed = int(time_str)
                    result = self.move(int(position_str))
                    self.settings.speed = old_speed
                    return "OK" if result else None
                return None

            if command.startswith("ID"):
                return "OK" if self.set_id(int(command[2:])) else None

            return None
        except Exception as exc:
            print(f"Error sending command to servo {self.id}: {exc}")
            return None
