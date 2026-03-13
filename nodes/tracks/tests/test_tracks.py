"""Tests for the tracks node command mapping."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tracks'))

from tracks.main import compute_joystick_command  # noqa: E402


def test_positive_x_produces_positive_angular_command() -> None:
    """Turning right on the stick should produce a right-turn command."""
    linear, angular, _, _ = compute_joystick_command(
        latest_joystick_x=1.0,
        latest_joystick_y=0.0,
        current_linear=0,
        current_angular=0,
    )

    assert linear == 0
    assert angular > 0


def test_negative_x_produces_negative_angular_command() -> None:
    """Turning left on the stick should produce a left-turn command."""
    linear, angular, _, _ = compute_joystick_command(
        latest_joystick_x=-1.0,
        latest_joystick_y=0.0,
        current_linear=0,
        current_angular=0,
    )

    assert linear == 0
    assert angular < 0
