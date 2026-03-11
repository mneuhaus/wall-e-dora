"""Data models for the Waveshare Servo Node."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ServoStatus:
    """Live telemetry returned by the servo."""

    position: int
    speed: int
    load: int
    voltage: float
    temperature: int
    moving: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert the status to a serializable dictionary."""
        return asdict(self)


@dataclass(slots=True)
class ServoModel:
    """Metadata derived from the servo model number."""

    model_number: int
    name: str
    max_position: int
    angle_range: int
    series: str
    torque: str

    @classmethod
    def from_model_number(cls, model_number: int) -> "ServoModel":
        """Return model information for known SC-series servos."""
        mapping = {
            4: ("SC09", 1023, 300, "SC", "2.3kg"),
            9: ("SC09", 1023, 300, "SC", "2.3kg"),
            0x0400: ("SC09", 1023, 300, "SC", "2.3kg"),
            0x0405: ("SC09", 1023, 300, "SC", "2.3kg"),
            0x0504: ("SC09", 1023, 300, "SC", "2.3kg"),
            15: ("SC15", 1023, 180, "SC", "17kg"),
            0x0F00: ("SC15", 1023, 180, "SC", "17kg"),
            0x0F05: ("SC15", 1023, 180, "SC", "17kg"),
            0x050F: ("SC15", 1023, 180, "SC", "17kg"),
            40: ("SC40", 1023, 180, "SC", "40kg"),
            0x2800: ("SC40", 1023, 180, "SC", "40kg"),
            60: ("SC60", 1023, 180, "SC", "60kg"),
            0x3C00: ("SC60", 1023, 180, "SC", "60kg"),
            14: ("SCS15", 1023, 180, "SCS", "15kg"),
            20: ("SCS20", 1023, 180, "SCS", "20kg"),
            35: ("SCS35", 1023, 180, "SCS", "35kg"),
        }
        name, max_position, angle_range, series, torque = mapping.get(
            model_number,
            ("Unknown", 1023, 180, "?", "?"),
        )
        return cls(
            model_number=model_number,
            name=name,
            max_position=max_position,
            angle_range=angle_range,
            series=series,
            torque=torque,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the model metadata to a serializable dictionary."""
        return asdict(self)


@dataclass(slots=True)
class ServoConfig:
    """Combined EEPROM and SRAM configuration for an SC-series servo."""

    id: int
    model_number: int
    model_name: str
    baud_rate: int
    baud_rate_bps: int
    return_delay: int
    response_status_level: int
    min_angle: int
    max_angle: int
    max_temperature: int
    max_voltage: int
    min_voltage: int
    max_torque: int
    phase: int
    unload_condition: int
    led_alarm: int
    p_coefficient: int
    d_coefficient: int
    i_coefficient: int
    min_startup_force: int
    cw_dead_zone: int
    ccw_dead_zone: int
    protection_current: int
    position_offset: int
    mode: int
    mode_name: str
    torque_enabled: bool
    acceleration: int
    goal_position: int
    goal_time: int
    goal_speed: int
    lock_state: bool
    raw_eeprom: list[int] = field(default_factory=list)
    raw_sram: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to a serializable dictionary."""
        return asdict(self)


@dataclass(slots=True)
class ServoSettings:
    """Represents persisted and live settings for a single servo."""

    id: int
    alias: str = ""
    min_pulse: int = 0
    max_pulse: int = 1023
    speed: int = 1000
    calibrated: bool = False
    position: int = 0
    invert: bool = False
    attached_control: str = ""
    gamepad_config: dict[str, Any] = field(default_factory=dict)
    voltage: float = 0.0
    temperature: int = 0
    load: int = 0
    moving: bool = False
    model_name: str = ""
    model_number: int = 0

    def __post_init__(self) -> None:
        """Normalize mutable default values after loading from JSON."""
        if self.gamepad_config is None:
            self.gamepad_config = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to a dictionary for config storage."""
        return asdict(self)

    def to_transport_dict(self) -> dict[str, Any]:
        """Convert settings to a frontend-friendly dictionary.

        The nested gamepad config is normalized so Arrow can build a stable
        struct array even when different servos have different mappings.
        """
        data = asdict(self)
        gamepad_config = self.gamepad_config or {}
        data["gamepad_config"] = {
            "control": gamepad_config.get("control", ""),
            "type": gamepad_config.get("type", ""),
            "mode": gamepad_config.get("mode", ""),
            "invert": bool(gamepad_config.get("invert", False)),
            "multiplier": float(gamepad_config.get("multiplier", 1)),
            "isAnalog": bool(gamepad_config.get("isAnalog", False)),
        }
        return data
