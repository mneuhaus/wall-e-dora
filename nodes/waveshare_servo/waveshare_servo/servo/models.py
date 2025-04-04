"""Data models for the Waveshare Servo Node."""

from dataclasses import asdict, dataclass, field
from typing import Dict, Optional, Any

@dataclass
class ServoSettings:
    """Represents settings for a single servo."""
    id: int
    alias: str = ""
    min_pulse: int = 0
    max_pulse: int = 1023
    speed: int = 1000
    calibrated: bool = False
    position: int = 0
    invert: bool = False
    attached_control: str = ""
    gamepad_config: Optional[Dict[str, Any]] = None
    voltage: float = 0.0  # Add voltage field for displaying power status

    def __post_init__(self):
        """Initialize empty dict for gamepad_config if None."""
        if self.gamepad_config is None:
            self.gamepad_config = {}

    def to_dict(self) -> dict:
        """Convert settings to dictionary for config/json."""
        return asdict(self)
