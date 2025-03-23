"""
Data models for the Waveshare Servo Node.
"""

from dataclasses import asdict, dataclass
from typing import Dict

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
