from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import random
import time
from typing import Any, Protocol

import pyarrow as pa

try:
    from sequence.soundtrack_analysis import load_soundtrack_analysis
except ModuleNotFoundError:
    from soundtrack_analysis import load_soundtrack_analysis

# ---------------------------------------------------------------------------
# Servo config loader — reads min_pulse / max_pulse from config/servo.json
# so sequence positions stay in sync with calibration.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVO_CONFIG_PATH = REPO_ROOT / "config" / "servo.json"

SERVO_ARM_LEFT = 2
SERVO_ARM_RIGHT = 13
SERVO_HEAD_LEFT = 6
SERVO_HEAD_RIGHT = 4
SERVO_HEAD_PIVOT = 14
SERVO_DOOR = 5

_DEFAULT_SERVO_RANGES: dict[int, tuple[int, int]] = {
    SERVO_ARM_LEFT: (50, 500),
    SERVO_ARM_RIGHT: (500, 940),
    SERVO_HEAD_LEFT: (0, 200),
    SERVO_HEAD_RIGHT: (0, 200),
    SERVO_HEAD_PIVOT: (404, 660),
    SERVO_DOOR: (700, 1023),
}


def _load_servo_ranges() -> dict[int, tuple[int, int]]:
    """Load (min_pulse, max_pulse) per servo from config/servo.json."""
    ranges = dict(_DEFAULT_SERVO_RANGES)
    if not SERVO_CONFIG_PATH.exists():
        return ranges
    try:
        data = json.loads(SERVO_CONFIG_PATH.read_text(encoding="utf-8"))
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            try:
                servo_id = int(key)
            except (TypeError, ValueError):
                continue
            ranges[servo_id] = (
                int(entry.get("min_pulse", 0)),
                int(entry.get("max_pulse", 1023)),
            )
    except Exception as exc:
        logging.warning("Could not load servo config: %s", exc)
    return ranges


_SERVO_RANGES = _load_servo_ranges()


def _servo_min(servo_id: int) -> int:
    return _SERVO_RANGES.get(servo_id, (0, 1023))[0]


def _servo_max(servo_id: int) -> int:
    return _SERVO_RANGES.get(servo_id, (0, 1023))[1]


def _servo_at(servo_id: int, fraction: float) -> int:
    """Position at *fraction* between min_pulse (0.0) and max_pulse (1.0)."""
    lo, hi = _SERVO_RANGES.get(servo_id, (0, 1023))
    return round(lo + (hi - lo) * max(0.0, min(1.0, fraction)))


# ---------------------------------------------------------------------------
# Servo positions — derived from config/servo.json
# ---------------------------------------------------------------------------

# Arms
ARM_LEFT_NEUTRAL = _servo_min(SERVO_ARM_LEFT)
ARM_LEFT_UP = _servo_max(SERVO_ARM_LEFT)
ARM_RIGHT_NEUTRAL = _servo_max(SERVO_ARM_RIGHT)
ARM_RIGHT_UP = _servo_at(SERVO_ARM_RIGHT, 0.318)

# Dance dead zone: bottom third of left arm range doesn't produce visible motion
DANCE_ARM_LEFT_MIN = _servo_at(SERVO_ARM_LEFT, 1 / 3)

# Head tilt
HEAD_LEFT_NEUTRAL = _servo_min(SERVO_HEAD_LEFT)
HEAD_LEFT_UP = _servo_at(SERVO_HEAD_LEFT, 0.6)
HEAD_RIGHT_NEUTRAL = _servo_max(SERVO_HEAD_RIGHT)
HEAD_RIGHT_UP = _servo_at(SERVO_HEAD_RIGHT, 0.425)

# Head pivot
HEAD_PIVOT_LEFT = _servo_at(SERVO_HEAD_PIVOT, 0.113)
HEAD_PIVOT_RIGHT = _servo_at(SERVO_HEAD_PIVOT, 0.688)
HEAD_PIVOT_CENTER = _servo_at(SERVO_HEAD_PIVOT, 0.375)

# Door
DOOR_CLOSED = _servo_min(SERVO_DOOR)
DOOR_OPEN = _servo_max(SERVO_DOOR)
DEFAULT_EYES = 'realistic-orange.gif'
TRACK_TURN_FAST = 68
TRACK_TURN_MEDIUM = 54
TRACK_TURN_SHIMMY = 38
DANCE_DEFAULT_TRACK_ID = 'dance:auto'
TRACK_LINEAR_DANCE_SMALL = 14
TRACK_LINEAR_DANCE_MEDIUM = 18
TRACK_LINEAR_DANCE_LARGE = 22
TRACK_ANGULAR_DANCE_WIDE = 24
TRACK_ANGULAR_DANCE_BROAD = 30


class OutputNode(Protocol):
    def send_output(
        self,
        output_id: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send a Dora output."""


@dataclass(frozen=True, slots=True)
class PlanStep:
    at: float
    output_id: str
    payload: list[Any]


@dataclass(slots=True)
class ActiveSequence:
    seq_id: str
    started_at: float
    steps: list[PlanStep]
    next_step_index: int = 0


class SequenceBuilder:
    def __init__(self) -> None:
        self._elapsed = 0.0
        self._steps: list[PlanStep] = []

    @property
    def elapsed(self) -> float:
        return self._elapsed

    def wait(self, seconds: float) -> None:
        self._elapsed += seconds

    def add(self, output_id: str, payload: list[Any]) -> None:
        self._steps.append(PlanStep(at=self._elapsed, output_id=output_id, payload=payload))

    def stop_sound(self) -> None:
        self.add('stop_sequence', [])

    def move_servo(self, servo_id: int, position: int) -> None:
        self.add('move_servo_sequence', [{'id': servo_id, 'position': position}])

    def move_tracks(self, linear: int, angular: int, duration: float = 0.0) -> None:
        self.add(
            'move_tracks_sequence',
            [{'linear': linear, 'angular': angular, 'duration': duration}],
        )

    def stop_tracks(self, duration: float = 0.0) -> None:
        self.move_tracks(0, 0, duration)

    def play_gif(self, filename: str) -> None:
        self.add('play_gif_sequence', [filename])

    def play_sound(self, filename: str) -> None:
        self.add('play_sound_sequence', [filename])

    def build(self) -> list[PlanStep]:
        steps = list(self._steps)
        steps.append(PlanStep(at=self._elapsed, output_id='stop_sequence', payload=[]))
        return steps



def extract_sequence_id(value: Any) -> str | None:
    try:
        if hasattr(value, 'to_pylist'):
            values = value.to_pylist()
            value = values[0] if values else None
        elif isinstance(value, list):
            value = value[0] if value else None

        if isinstance(value, dict):
            sequence_id = value.get('id')
            return sequence_id if isinstance(sequence_id, str) else None
        return value
    except Exception:
        return None


def extract_first_payload(value: Any) -> Any:
    """Return the first logical payload item from Arrow/list inputs."""
    try:
        if hasattr(value, 'to_pylist'):
            values = value.to_pylist()
            return values[0] if values else None
        if isinstance(value, list):
            return value[0] if value else None
        return value
    except Exception:
        return None



def neutral_pose(
    builder: SequenceBuilder,
    *,
    close_door: bool = True,
    keep_eyes: bool = False,
) -> None:
    """Return the robot to a safe, neutral pose."""
    if not keep_eyes:
        builder.play_gif(DEFAULT_EYES)
    if close_door:
        builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    builder.wait(0.15)
    builder.move_servo(13, ARM_RIGHT_NEUTRAL)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.wait(0.2)
    builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.2)



def build_hands_up(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.play_gif('lets-go.gif')
    builder.play_sound('freudiges-jubeln.mp3')
    builder.move_servo(2, ARM_LEFT_UP)
    builder.wait(0.15)
    builder.move_servo(13, ARM_RIGHT_UP)
    builder.wait(2.0)
    builder.move_servo(2, max(0, ARM_LEFT_UP - 60))
    builder.move_servo(13, min(ARM_RIGHT_NEUTRAL, ARM_RIGHT_UP + 70))
    builder.wait(0.4)
    builder.move_servo(2, ARM_LEFT_UP)
    builder.move_servo(13, ARM_RIGHT_UP)
    builder.wait(0.4)
    builder.move_servo(13, ARM_RIGHT_NEUTRAL)
    builder.wait(0.2)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    neutral_pose(builder, keep_eyes=True)



def build_candy(builder: SequenceBuilder) -> None:
    builder.play_gif('ghibli-candy.gif')
    builder.play_sound('fragendes-seufzen.mp3')
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(5, DOOR_OPEN)
    builder.wait(1.2)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.wait(1.0)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.wait(0.3)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.4)
    builder.move_servo(2, 220)
    builder.wait(0.5)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    builder.wait(0.4)
    builder.move_servo(2, 120)
    builder.wait(0.5)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    builder.wait(0.3)
    builder.move_servo(13, 780)
    builder.wait(0.4)
    builder.move_servo(13, ARM_RIGHT_NEUTRAL)
    neutral_pose(builder, keep_eyes=True)



def build_party(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.play_gif('lets-dance.gif')
    builder.play_sound('träumerisches-summen.mp3')

    while builder.elapsed < 7.9:
        builder.move_servo(2, 220)
        builder.wait(0.15)
        builder.move_servo(13, 780)
        builder.move_servo(6, HEAD_LEFT_UP)
        builder.wait(0.22)
        builder.move_servo(6, HEAD_LEFT_NEUTRAL)
        builder.wait(0.15)
        builder.move_servo(2, ARM_LEFT_NEUTRAL)
        builder.wait(0.15)
        builder.move_servo(13, ARM_RIGHT_NEUTRAL)
        builder.move_servo(4, HEAD_RIGHT_UP)
        builder.wait(0.22)
        builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
        builder.wait(0.15)
        builder.move_servo(14, HEAD_PIVOT_LEFT)
        builder.wait(0.14)
        builder.move_servo(14, HEAD_PIVOT_CENTER)
        builder.wait(0.14)
        builder.move_servo(14, HEAD_PIVOT_RIGHT)
        builder.wait(0.14)
        builder.move_servo(14, HEAD_PIVOT_CENTER)
        builder.wait(0.14)

    neutral_pose(builder, keep_eyes=True)



def build_wave_hello(builder: SequenceBuilder) -> None:
    builder.play_gif('emotion-love.gif')
    builder.play_sound('fröhliches-piepen.mp3')
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.2)

    for _ in range(4):
        builder.move_servo(2, ARM_LEFT_UP)
        builder.wait(0.25)
        builder.move_servo(2, 220)
        builder.wait(0.25)

    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.wait(0.15)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.15)
    builder.move_servo(14, HEAD_PIVOT_RIGHT)
    builder.wait(0.15)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.2)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    neutral_pose(builder, keep_eyes=True)



def build_curious_scan(builder: SequenceBuilder) -> None:
    builder.play_gif('ghibli-landscape.gif')
    builder.play_sound('neugieriges-miauen.mp3')
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.2)

    while builder.elapsed < 9.0:
        builder.move_servo(14, HEAD_PIVOT_LEFT)
        builder.wait(0.25)
        builder.move_servo(14, HEAD_PIVOT_CENTER)
        builder.wait(0.25)
        builder.move_servo(14, HEAD_PIVOT_RIGHT)
        builder.wait(0.25)
        builder.move_servo(14, HEAD_PIVOT_CENTER)
        builder.wait(0.25)
        builder.move_servo(6, HEAD_LEFT_UP)
        builder.wait(0.22)
        builder.move_servo(6, HEAD_LEFT_NEUTRAL)
        builder.wait(0.18)
        builder.move_servo(4, HEAD_RIGHT_UP)
        builder.wait(0.22)
        builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
        builder.wait(0.18)

    neutral_pose(builder, keep_eyes=True)



def build_peekaboo(builder: SequenceBuilder) -> None:
    builder.play_gif('lets-go.gif')
    builder.play_sound('überraschtes-ah.mp3')
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
    builder.move_servo(5, DOOR_OPEN)
    builder.wait(1.5)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.wait(0.7)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.wait(0.3)
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.wait(0.35)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.25)
    builder.move_servo(13, 780)
    builder.wait(0.4)
    builder.move_servo(13, ARM_RIGHT_NEUTRAL)
    builder.move_servo(5, DOOR_CLOSED)
    builder.wait(0.3)
    neutral_pose(builder, close_door=True, keep_eyes=True)



def build_spin_wiggle(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.play_gif('lets-dance.gif')
    builder.play_sound('freudiges-jubeln.mp3')
    builder.move_servo(2, 210)
    builder.move_servo(13, 780)
    builder.wait(0.15)

    builder.move_tracks(0, TRACK_TURN_FAST, 0.45)
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.wait(0.45)
    builder.stop_tracks(0.1)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.wait(0.1)

    builder.move_tracks(0, -TRACK_TURN_FAST, 0.45)
    builder.move_servo(14, HEAD_PIVOT_RIGHT)
    builder.move_servo(4, HEAD_RIGHT_UP)
    builder.wait(0.45)
    builder.stop_tracks(0.1)
    builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
    builder.wait(0.1)

    builder.move_tracks(0, TRACK_TURN_SHIMMY, 0.16)
    builder.move_servo(2, ARM_LEFT_UP)
    builder.wait(0.16)
    builder.move_tracks(0, -TRACK_TURN_SHIMMY, 0.16)
    builder.move_servo(13, ARM_RIGHT_UP)
    builder.wait(0.16)
    builder.stop_tracks(0.1)
    builder.move_servo(2, 210)
    builder.move_servo(13, 780)
    builder.wait(0.1)
    neutral_pose(builder, keep_eyes=True)



def build_double_take(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.play_gif('lets-go.gif')
    builder.play_sound('überraschtes-ah.mp3')
    builder.wait(0.1)

    builder.move_tracks(0, TRACK_TURN_MEDIUM, 0.18)
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.wait(0.18)
    builder.stop_tracks(0.08)
    builder.wait(0.08)

    builder.move_tracks(-24, -TRACK_TURN_FAST, 0.34)
    builder.move_servo(14, HEAD_PIVOT_RIGHT)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.move_servo(4, HEAD_RIGHT_UP)
    builder.move_servo(5, DOOR_OPEN)
    builder.wait(0.34)
    builder.stop_tracks(0.08)
    builder.move_servo(5, DOOR_CLOSED)
    builder.wait(0.08)

    builder.move_tracks(0, TRACK_TURN_MEDIUM, 0.14)
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.move_servo(2, 180)
    builder.wait(0.14)
    builder.stop_tracks(0.1)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
    builder.wait(0.1)
    neutral_pose(builder, keep_eyes=True)



def build_shimmy(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.play_gif('lets-dance.gif')
    builder.play_sound('fröhliches-piepen.mp3')
    builder.move_servo(2, 220)
    builder.move_servo(13, 780)
    builder.wait(0.15)

    for index in range(4):
        builder.move_tracks(0, TRACK_TURN_SHIMMY, 0.14)
        builder.move_servo(14, HEAD_PIVOT_LEFT)
        builder.move_servo(2, ARM_LEFT_UP if index % 2 == 0 else 220)
        builder.move_servo(13, 780 if index % 2 == 0 else ARM_RIGHT_UP)
        builder.wait(0.14)
        builder.move_tracks(0, -TRACK_TURN_SHIMMY, 0.14)
        builder.move_servo(14, HEAD_PIVOT_RIGHT)
        builder.move_servo(2, 220 if index % 2 == 0 else ARM_LEFT_UP)
        builder.move_servo(13, ARM_RIGHT_UP if index % 2 == 0 else 780)
        builder.wait(0.14)

    builder.stop_tracks(0.12)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.wait(0.12)
    neutral_pose(builder, keep_eyes=True)



def build_pirouette(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.play_gif('lets-dance.gif')
    builder.play_sound('freudiges-trällern.mp3')
    builder.move_servo(2, 180)
    builder.move_servo(13, 820)
    builder.wait(0.16)

    # Four longer turning phases make the pirouette read as a full spin instead
    # of the previous partial quarter-turn.
    turn_duration = 1.15

    builder.move_tracks(0, TRACK_TURN_MEDIUM, turn_duration)
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.wait(turn_duration)

    builder.move_tracks(0, TRACK_TURN_MEDIUM, turn_duration)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.move_servo(4, HEAD_RIGHT_UP)
    builder.move_servo(2, ARM_LEFT_UP)
    builder.wait(turn_duration)

    builder.move_tracks(0, TRACK_TURN_MEDIUM, turn_duration)
    builder.move_servo(14, HEAD_PIVOT_RIGHT)
    builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
    builder.move_servo(13, ARM_RIGHT_UP)
    builder.wait(turn_duration)

    builder.move_tracks(0, TRACK_TURN_MEDIUM, turn_duration)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    builder.wait(turn_duration)

    builder.stop_tracks(0.14)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.move_servo(13, ARM_RIGHT_NEUTRAL)
    builder.wait(0.14)
    neutral_pose(builder, keep_eyes=True)


def build_suche(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.play_gif('ghibli-landscape.gif')
    builder.play_sound('fragendes-seufzen.mp3')
    builder.wait(0.15)

    builder.move_tracks(0, TRACK_TURN_SHIMMY, 0.38)
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.move_servo(2, 160)
    builder.wait(0.38)
    builder.stop_tracks(0.12)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.wait(0.12)

    builder.move_tracks(0, -TRACK_TURN_SHIMMY, 0.5)
    builder.move_servo(14, HEAD_PIVOT_RIGHT)
    builder.move_servo(4, HEAD_RIGHT_UP)
    builder.move_servo(13, 805)
    builder.wait(0.5)
    builder.stop_tracks(0.12)
    builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
    builder.wait(0.12)

    builder.move_tracks(0, TRACK_TURN_SHIMMY, 0.26)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(2, 120)
    builder.move_servo(13, 760)
    builder.wait(0.26)

    builder.stop_tracks(0.12)
    builder.wait(0.12)
    neutral_pose(builder, keep_eyes=True)


def build_idle_listen(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.play_sound('fragendes-seufzen.mp3')
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.move_servo(6, HEAD_LEFT_UP)
    builder.move_servo(2, 120)
    builder.wait(0.45)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(6, HEAD_LEFT_NEUTRAL)
    builder.wait(0.25)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    builder.wait(0.15)
    neutral_pose(builder, keep_eyes=True)



def build_idle_peek(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.play_sound('neugieriges-miauen.mp3')
    builder.move_servo(14, HEAD_PIVOT_RIGHT)
    builder.move_servo(4, HEAD_RIGHT_UP)
    builder.move_servo(13, 820)
    builder.wait(0.4)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(4, HEAD_RIGHT_NEUTRAL)
    builder.wait(0.25)
    builder.move_servo(13, ARM_RIGHT_NEUTRAL)
    builder.wait(0.15)
    neutral_pose(builder, keep_eyes=True)



def build_idle_fidget(builder: SequenceBuilder) -> None:
    builder.move_servo(5, DOOR_CLOSED)
    builder.play_sound('freudiges-trällern.mp3')
    builder.move_servo(14, HEAD_PIVOT_LEFT)
    builder.move_servo(2, 150)
    builder.wait(0.22)
    builder.move_servo(14, HEAD_PIVOT_RIGHT)
    builder.move_servo(13, 800)
    builder.wait(0.22)
    builder.move_servo(14, HEAD_PIVOT_CENTER)
    builder.move_servo(2, ARM_LEFT_NEUTRAL)
    builder.move_servo(13, ARM_RIGHT_NEUTRAL)
    builder.wait(0.2)
    neutral_pose(builder, keep_eyes=True)


def dance_arm_pose(builder: SequenceBuilder, left: int, right: int) -> None:
    # The hardcoded left values are systematically lower than the right values
    # because the choreographer wrote them as fractions of the full servo range
    # while the right values are already in the visible range.  Blend the left
    # arm toward the right arm's visual level so both arms look equally dynamic.
    left_range = ARM_LEFT_UP - ARM_LEFT_NEUTRAL
    right_range = ARM_RIGHT_NEUTRAL - ARM_RIGHT_UP
    left_level = clamp_float((left - ARM_LEFT_NEUTRAL) / max(1, left_range), 0.0, 1.0)
    right_level = clamp_float((ARM_RIGHT_NEUTRAL - right) / max(1, right_range), 0.0, 1.0)
    blended = clamp_float(left_level * 0.15 + right_level * 0.85, 0.0, 1.0)
    builder.move_servo(2, left_arm_for(blended))
    builder.move_servo(13, right)


def dance_head_pose(builder: SequenceBuilder, pivot: int, left: int, right: int) -> None:
    builder.move_servo(14, pivot)
    builder.move_servo(6, left)
    builder.move_servo(4, right)


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def lerp(start: float, end: float, amount: float) -> float:
    return start + ((end - start) * clamp_float(amount, 0.0, 1.0))


def head_pivot_for(offset: float) -> int:
    normalized = clamp_float(offset, -1.0, 1.0)
    if normalized >= 0:
        return round(lerp(HEAD_PIVOT_CENTER, HEAD_PIVOT_RIGHT, normalized))
    return round(lerp(HEAD_PIVOT_CENTER, HEAD_PIVOT_LEFT, abs(normalized)))


def left_arm_for(level: float) -> int:
    return round(lerp(DANCE_ARM_LEFT_MIN, ARM_LEFT_UP, level))


def right_arm_for(level: float) -> int:
    return round(lerp(ARM_RIGHT_NEUTRAL, ARM_RIGHT_UP, level))


def head_left_for(level: float) -> int:
    return round(lerp(HEAD_LEFT_NEUTRAL, HEAD_LEFT_UP, level))


def head_right_for(level: float) -> int:
    return round(lerp(HEAD_RIGHT_NEUTRAL, HEAD_RIGHT_UP, level))


def dance_arm_levels(builder: SequenceBuilder, left: float, right: float) -> None:
    # Bypass dance_arm_pose to avoid double-remapping: left_arm_for already
    # maps into the visible range, so amplify_left_dance_arm_position must
    # not be applied a second time.
    builder.move_servo(2, left_arm_for(left))
    builder.move_servo(13, right_arm_for(right))


def dance_head_levels(
    builder: SequenceBuilder,
    pivot_offset: float,
    left_level: float,
    right_level: float,
) -> None:
    dance_head_pose(
        builder,
        head_pivot_for(pivot_offset),
        head_left_for(left_level),
        head_right_for(right_level),
    )


def dance_section_intensity(section: dict[str, Any], base_energy: float) -> float:
    energy = float(section.get('energy') or 0.0)
    accent_density = float(section.get('accent_density') or 0.0)
    role = str(section.get('role') or 'groove')
    role_bias = {
        'intro': -0.12,
        'breath': -0.18,
        'breakdown': -0.08,
        'groove': 0.0,
        'build': 0.1,
        'peak': 0.2,
        'finale': 0.16,
    }.get(role, 0.0)
    return clamp_float((base_energy * 0.45) + (energy * 0.55) + (accent_density * 0.14) + role_bias, 0.22, 1.0)


def amplify_left_dance_arm_position(position: int) -> int:
    """Remap left arm positions from the full range into the visible range.

    The left arm linkage has a mechanical dead zone below DANCE_ARM_LEFT_MIN
    where the servo moves but the arm doesn't visibly respond.  The right arm
    has a similar dead zone but its choreography values are already written in
    the visible range, so the right arm naturally gets a ~1.5x amplification
    (full_range / visible_range).  We apply the same scaling here so that
    matching fractions of full range produce matching visible motion on both
    arms.
    """
    full_range = ARM_LEFT_UP - ARM_LEFT_NEUTRAL
    visible_range = ARM_LEFT_UP - DANCE_ARM_LEFT_MIN
    if full_range <= 0 or visible_range <= 0:
        return DANCE_ARM_LEFT_MIN
    fraction = clamp_float((position - ARM_LEFT_NEUTRAL) / full_range, 0.0, 1.0)
    amplified = clamp_float(fraction * full_range / visible_range, 0.0, 1.0)
    return round(DANCE_ARM_LEFT_MIN + amplified * visible_range)


class DanceContext:
    """Holds state for a single dance performance with seeded randomness."""

    def __init__(self, seed: str, accent_times: list[float], song_offset: float = 0.0):
        self.rng = random.Random(seed)
        self.accent_times = sorted(accent_times)
        self.song_offset = song_offset
        self._highlight_count = 0
        self._max_highlights = 3
        self._last_phrase = ''
        self._phrase_counter = 0
        self._last_accent_elapsed = -10.0

    def micro(self, base: float, spread: float = 0.1) -> float:
        return clamp_float(base + self.rng.uniform(-spread, spread), 0.0, 1.0)

    def micro_int(self, base: int, spread: int = 12) -> int:
        return base + self.rng.randint(-spread, spread)

    def pick(self, options: list | tuple):
        return self.rng.choice(options)

    def chance(self, probability: float) -> bool:
        return self.rng.random() < probability

    def accents_between(self, song_start: float, song_end: float) -> list[float]:
        return [t for t in self.accent_times if song_start <= t <= song_end]

    def should_highlight(self, role: str, intensity: float) -> bool:
        if role not in ('peak', 'finale', 'build'):
            return False
        if self._highlight_count >= self._max_highlights:
            return False
        threshold = 0.7 if role == 'peak' else 0.85
        if intensity < threshold:
            return False
        if self.chance(0.55):
            self._highlight_count += 1
            return True
        return False

    def should_accent_hit(self, builder_elapsed: float, beat: float) -> bool:
        if builder_elapsed - self._last_accent_elapsed < beat * 2.5:
            return False
        if self.chance(0.65):
            self._last_accent_elapsed = builder_elapsed
            return True
        return False

    def next_phrase(self, phrase_names: tuple[str, ...]) -> str:
        self._phrase_counter += 1
        if len(phrase_names) <= 1:
            name = phrase_names[0]
        elif len(phrase_names) == 2:
            name = phrase_names[self._phrase_counter % 2]
            if name == self._last_phrase and self.chance(0.4):
                name = phrase_names[(self._phrase_counter + 1) % 2]
        else:
            available = [p for p in phrase_names if p != self._last_phrase]
            name = self.rng.choice(available) if available else self.rng.choice(phrase_names)
        self._last_phrase = name
        return name

    def direction_for(self, index: int) -> int:
        base = -1 if index % 2 == 0 else 1
        if self.chance(0.2):
            return -base
        return base

    def ramped_intensity(self, base_intensity: float, position: float, role: str) -> float:
        if role == 'build':
            ramp = 0.7 + (position * 0.3)
        elif role == 'peak':
            ramp = 0.85 + (position * 0.15)
        elif role in ('intro', 'breath'):
            ramp = 0.8 + (position * 0.15)
        else:
            ramp = 0.88 + (position * 0.12)
        return clamp_float(base_intensity * ramp, 0.22, 1.0)


def accent_hit(builder: SequenceBuilder, ctx: DanceContext, intensity: float) -> float:
    """Insert a sharp reactive move on a musical accent."""
    start = builder.elapsed
    hit_type = ctx.pick(['door_snap', 'arm_pop_left', 'arm_pop_right', 'head_whip', 'full_snap'])

    if hit_type == 'door_snap':
        pos = round(lerp(810, 930, intensity))
        builder.move_servo(5, pos)
        builder.wait(0.09)
        builder.move_servo(5, DOOR_CLOSED)
    elif hit_type == 'arm_pop_left':
        dance_arm_levels(builder, ctx.micro(0.95, 0.05), ctx.micro(0.35, 0.08))
        builder.wait(0.1)
        dance_arm_levels(builder, ctx.micro(0.5, 0.08), ctx.micro(0.5, 0.08))
    elif hit_type == 'arm_pop_right':
        dance_arm_levels(builder, ctx.micro(0.35, 0.08), ctx.micro(0.95, 0.05))
        builder.wait(0.1)
        dance_arm_levels(builder, ctx.micro(0.5, 0.08), ctx.micro(0.5, 0.08))
    elif hit_type == 'head_whip':
        direction = ctx.pick([-1, 1])
        dance_head_levels(builder, 0.55 * direction, ctx.micro(0.78, 0.08), ctx.micro(0.15, 0.06))
        builder.wait(0.12)
        dance_head_levels(builder, 0.0, 0.35, 0.35)
    else:
        dance_arm_levels(builder, ctx.micro(0.92, 0.06), ctx.micro(0.92, 0.06))
        dance_head_levels(builder, 0.0, ctx.micro(0.82, 0.08), ctx.micro(0.82, 0.08))
        pos = round(lerp(840, 930, intensity))
        builder.move_servo(5, pos)
        builder.wait(0.1)
        builder.move_servo(5, DOOR_CLOSED)

    return builder.elapsed - start


def highlight_both_arms_up(builder: SequenceBuilder, ctx: DanceContext, beat: float, intensity: float) -> float:
    """Both arms full up with door burst - the crowd-pleaser."""
    start = builder.elapsed
    dance_arm_levels(builder, 1.0, 1.0)
    dance_head_levels(builder, 0.0, ctx.micro(0.88, 0.08), ctx.micro(0.88, 0.08))
    builder.move_servo(5, round(lerp(870, 960, intensity)))
    builder.wait(beat * 1.3)
    builder.move_servo(5, DOOR_CLOSED)
    dance_arm_levels(builder, ctx.micro(0.48, 0.1), ctx.micro(0.52, 0.1))
    dance_head_levels(builder, 0.0, 0.3, 0.3)
    builder.wait(beat * 0.4)
    return builder.elapsed - start


def highlight_freeze(builder: SequenceBuilder, ctx: DanceContext, beat: float, intensity: float) -> float:
    """Sudden freeze in a dramatic pose - builds tension."""
    start = builder.elapsed
    direction = ctx.pick([-1, 1])
    if direction < 0:
        dance_arm_levels(builder, ctx.micro(0.88, 0.08), ctx.micro(0.18, 0.08))
    else:
        dance_arm_levels(builder, ctx.micro(0.18, 0.08), ctx.micro(0.88, 0.08))
    dance_head_levels(builder, 0.42 * direction, 0.12, 0.12)
    builder.stop_tracks(0.06)
    builder.wait(beat * 1.6)
    dance_head_levels(builder, 0.0, 0.42, 0.42)
    dance_arm_levels(builder, 0.5, 0.5)
    builder.wait(beat * 0.35)
    return builder.elapsed - start


def highlight_spin_burst(builder: SequenceBuilder, ctx: DanceContext, beat: float, intensity: float) -> float:
    """Quick energetic spin with arms out."""
    start = builder.elapsed
    direction = ctx.pick([-1, 1])
    dance_arm_levels(builder, ctx.micro(0.72, 0.08), ctx.micro(0.72, 0.08))
    dance_head_levels(builder, -0.28 * direction, 0.18, 0.18)
    turn = round(52 + (intensity * 22))
    builder.move_tracks(0, turn * direction, beat * 2.6)
    builder.wait(beat * 2.1)
    builder.stop_tracks(0.14)
    dance_head_levels(builder, 0.0, 0.5, 0.5)
    dance_arm_levels(builder, 0.5, 0.5)
    builder.wait(beat * 0.3)
    return builder.elapsed - start


def highlight_door_drama(builder: SequenceBuilder, ctx: DanceContext, beat: float, intensity: float) -> float:
    """Dramatic slow door open with head tilt, then snap shut."""
    start = builder.elapsed
    dance_head_levels(builder, ctx.micro(0.0, 0.15), ctx.micro(0.7, 0.1), ctx.micro(0.7, 0.1))
    dance_arm_levels(builder, ctx.micro(0.6, 0.1), ctx.micro(0.6, 0.1))
    builder.move_servo(5, round(lerp(880, 1000, intensity)))
    builder.wait(beat * 1.0)
    dance_arm_levels(builder, 1.0, 1.0)
    builder.wait(beat * 0.5)
    builder.move_servo(5, DOOR_CLOSED)
    dance_arm_levels(builder, 0.4, 0.4)
    dance_head_levels(builder, 0.0, 0.2, 0.2)
    builder.wait(beat * 0.3)
    return builder.elapsed - start


def transition_breath(builder: SequenceBuilder, ctx: DanceContext, beat: float) -> float:
    """Brief breathing moment between sections."""
    start = builder.elapsed
    dance_head_levels(builder, ctx.micro(0.0, 0.12), ctx.micro(0.3, 0.1), ctx.micro(0.3, 0.1))
    dance_arm_levels(builder, ctx.micro(0.42, 0.08), ctx.micro(0.42, 0.08))
    builder.wait(beat * clamp_float(ctx.rng.uniform(0.4, 0.7), 0.35, 0.75))
    return builder.elapsed - start


def dance_door_pulse(builder: SequenceBuilder, *, position: int = 820, hold: float = 0.18) -> None:
    builder.move_servo(5, position)
    builder.wait(hold)
    builder.move_servo(5, DOOR_CLOSED)


def dance_track_move(
    builder: SequenceBuilder,
    *,
    linear: int = 0,
    angular: int = 0,
    duration: float,
    linear_scale: float = 1.0,
    angular_scale: float = 1.0,
) -> None:
    """Emit a dance-oriented track move with tunable radius scaling."""
    builder.move_tracks(
        round(linear * linear_scale),
        round(angular * angular_scale),
        duration,
    )


def build_define_dancing_phrase(builder: SequenceBuilder, *, beat: float, variant: int) -> None:
    """A four-beat phrase tuned to Define Dancing's flowing duet feel."""
    phrase = variant % 4

    if phrase == 0:
        builder.play_gif('lets-dance.gif')
        dance_head_pose(builder, HEAD_PIVOT_LEFT + 22, 22, 178)
        dance_arm_pose(builder, 240, 760)
        builder.move_tracks(10, 18, beat * 1.3)
        builder.wait(beat)
        dance_head_pose(builder, HEAD_PIVOT_CENTER, 70, 205)
        dance_arm_pose(builder, 170, 820)
        builder.wait(beat)
        dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 18, 172)
        dance_arm_pose(builder, 205, 700)
        builder.move_tracks(-10, -18, beat * 1.3)
        builder.wait(beat)
        dance_door_pulse(builder, position=820, hold=beat * 0.28)
        builder.wait(beat * 0.45)
        return

    if phrase == 1:
        builder.play_gif('emotion-love.gif')
        dance_head_pose(builder, HEAD_PIVOT_LEFT + 40, 18, 170)
        dance_arm_pose(builder, 275, 760)
        builder.move_tracks(0, 26, beat * 1.8)
        builder.wait(beat * 1.2)
        dance_head_pose(builder, HEAD_PIVOT_CENTER, 56, 198)
        dance_arm_pose(builder, 190, 790)
        builder.wait(beat * 0.8)
        dance_head_pose(builder, HEAD_PIVOT_RIGHT - 44, 18, 170)
        dance_arm_pose(builder, 210, 680)
        builder.move_tracks(0, -26, beat * 1.8)
        builder.wait(beat * 1.2)
        dance_door_pulse(builder, position=780, hold=beat * 0.22)
        builder.wait(beat * 0.4)
        return

    if phrase == 2:
        builder.play_gif('iris-yellow2.gif')
        dance_head_pose(builder, HEAD_PIVOT_CENTER, 20, 170)
        dance_arm_pose(builder, 255, 725)
        builder.move_tracks(10, 0, beat * 0.9)
        builder.wait(beat * 0.75)
        dance_head_pose(builder, HEAD_PIVOT_LEFT + 18, 82, 206)
        dance_arm_pose(builder, 180, 830)
        builder.move_tracks(-10, 14, beat * 0.8)
        builder.wait(beat * 0.75)
        dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 32, 182)
        dance_arm_pose(builder, 228, 708)
        builder.move_tracks(0, -14, beat * 0.8)
        builder.wait(beat * 0.75)
        dance_door_pulse(builder, position=845, hold=beat * 0.24)
        dance_head_pose(builder, HEAD_PIVOT_CENTER, 70, 205)
        builder.wait(beat * 0.8)
        return

    builder.play_gif('lets-dance.gif')
    dance_head_pose(builder, HEAD_PIVOT_LEFT + 28, 28, 176)
    dance_arm_pose(builder, 250, 742)
    builder.move_tracks(12, 20, beat * 1.1)
    builder.wait(beat)
    dance_head_pose(builder, HEAD_PIVOT_RIGHT - 28, 28, 176)
    dance_arm_pose(builder, 170, 822)
    builder.move_tracks(-12, -20, beat * 1.1)
    builder.wait(beat)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 170)
    dance_arm_pose(builder, 300, 700)
    builder.move_tracks(0, 16, beat * 0.85)
    builder.wait(beat)
    dance_door_pulse(builder, position=830, hold=beat * 0.24)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 70, 205)
    builder.move_tracks(0, -16, beat * 0.5)
    builder.wait(beat * 0.5)


def build_define_dancing_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
) -> None:
    """A full on-robot choreographed performance for Define Dancing."""
    beat = 60.0 / 108.0
    finale_buffer = 9.0

    builder.play_gif('lets-dance.gif')
    builder.play_sound(filename)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
    dance_arm_pose(builder, 210, 770)
    builder.wait(beat * 2)

    phrase_index = 0
    while builder.elapsed < max(beat * 4, duration_seconds - finale_buffer):
        build_define_dancing_phrase(builder, beat=beat, variant=phrase_index)
        phrase_index += 1

    builder.play_gif('emotion-love.gif')
    dance_head_pose(builder, HEAD_PIVOT_LEFT + 36, 18, 170)
    dance_arm_pose(builder, 290, 740)
    builder.move_tracks(0, 22, beat * 1.8)
    builder.wait(beat * 1.6)
    dance_head_pose(builder, HEAD_PIVOT_RIGHT - 36, 18, 170)
    dance_arm_pose(builder, 210, 680)
    builder.move_tracks(0, -22, beat * 1.8)
    builder.wait(beat * 1.6)
    builder.move_servo(5, 860)
    builder.wait(beat)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 74, 206)
    dance_arm_pose(builder, 160, 820)
    builder.wait(beat * 1.2)
    neutral_pose(builder, keep_eyes=True)


def build_imperial_march_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
    bpm: float,
) -> None:
    """A heavier, more deliberate show for march-like tracks."""
    beat = 60.0 / max(76.0, bpm)
    finale_buffer = 7.0

    builder.play_gif('danger.gif')
    builder.play_sound(filename)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 14, 176)
    dance_arm_pose(builder, 120, 820)
    builder.wait(beat * 2)

    variant = 0
    while builder.elapsed < max(beat * 4, duration_seconds - finale_buffer):
        if variant % 2 == 0:
            builder.play_gif('danger.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 12, 10, 176)
            dance_arm_pose(builder, 105, 835)
            dance_track_move(
                builder,
                linear=TRACK_LINEAR_DANCE_MEDIUM,
                angular=TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 1.0,
                linear_scale=1.28,
                angular_scale=1.12,
            )
            builder.wait(beat)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 12, 10, 176)
            dance_arm_pose(builder, 145, 785)
            dance_track_move(
                builder,
                linear=-TRACK_LINEAR_DANCE_MEDIUM,
                angular=-TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 1.0,
                linear_scale=1.28,
                angular_scale=1.12,
            )
            builder.wait(beat)
            dance_door_pulse(builder, position=790, hold=beat * 0.2)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 14, 176)
            builder.wait(beat * 0.65)
        else:
            builder.play_gif('iris-yellow.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 18, 12, 178)
            dance_arm_pose(builder, 95, 845)
            dance_track_move(
                builder,
                linear=TRACK_LINEAR_DANCE_SMALL,
                angular=TRACK_ANGULAR_DANCE_BROAD,
                duration=beat * 1.08,
                linear_scale=1.32,
                angular_scale=1.14,
            )
            builder.wait(beat)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 188)
            dance_arm_pose(builder, 140, 790)
            builder.wait(beat * 0.5)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 12, 178)
            dance_arm_pose(builder, 120, 820)
            dance_track_move(
                builder,
                linear=-TRACK_LINEAR_DANCE_SMALL,
                angular=-TRACK_ANGULAR_DANCE_BROAD,
                duration=beat * 1.08,
                linear_scale=1.32,
                angular_scale=1.14,
            )
            builder.wait(beat)
            dance_door_pulse(builder, position=835, hold=beat * 0.14)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 14, 176)
            builder.wait(beat * 0.75)
        variant += 1

    builder.play_gif('lets-go.gif')
    dance_head_pose(builder, HEAD_PIVOT_LEFT + 20, 12, 176)
    dance_arm_pose(builder, 110, 830)
    dance_track_move(
        builder,
        angular=TRACK_ANGULAR_DANCE_BROAD,
        duration=beat * 1.78,
        angular_scale=1.22,
    )
    builder.wait(beat * 1.3)
    dance_head_pose(builder, HEAD_PIVOT_RIGHT - 20, 12, 176)
    dance_arm_pose(builder, 140, 790)
    dance_track_move(
        builder,
        angular=-TRACK_ANGULAR_DANCE_BROAD,
        duration=beat * 1.78,
        angular_scale=1.22,
    )
    builder.wait(beat * 1.3)
    builder.move_servo(5, 860)
    builder.wait(beat * 0.45)
    builder.move_servo(5, DOOR_CLOSED)
    builder.wait(beat * 0.55)
    neutral_pose(builder, keep_eyes=True)


def build_disco_dance_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
    bpm: float,
) -> None:
    """Confident disco phrases with mirrored sways and visible upper-body variation."""
    beat = 60.0 / max(84.0, bpm)
    finale_buffer = 6.5

    builder.play_gif('lets-dance.gif')
    builder.play_sound(filename)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
    dance_arm_pose(builder, 220, 780)
    builder.wait(beat * 2)

    variant = 0
    while builder.elapsed < max(beat * 4, duration_seconds - finale_buffer):
        phrase = variant % 4
        if phrase == 0:
            builder.play_gif('lets-dance.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 32, 12, 176)
            dance_arm_pose(builder, 320, 700)
            builder.move_tracks(10, 20, beat * 0.9)
            builder.wait(beat * 0.85)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 68, 202)
            dance_arm_pose(builder, 180, 840)
            builder.wait(beat * 0.35)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 32, 12, 176)
            dance_arm_pose(builder, 140, 865)
            builder.move_tracks(-10, -20, beat * 0.9)
            builder.wait(beat * 0.85)
            dance_door_pulse(builder, position=815, hold=beat * 0.18)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            builder.wait(beat * 0.45)
        elif phrase == 1:
            builder.play_gif('emotion-love.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 22, 76, 205)
            dance_arm_pose(builder, 285, 715)
            builder.move_tracks(0, 22, beat * 0.85)
            builder.wait(beat * 0.8)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 22, 24, 184)
            dance_arm_pose(builder, 175, 855)
            builder.move_tracks(0, -22, beat * 0.85)
            builder.wait(beat * 0.8)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 170)
            dance_arm_pose(builder, 250, 740)
            builder.move_tracks(8, 0, beat * 0.55)
            builder.wait(beat * 0.5)
            builder.move_tracks(-8, 0, beat * 0.55)
            builder.wait(beat * 0.5)
        elif phrase == 2:
            builder.play_gif('iris-yellow2.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 16, 18, 176)
            dance_arm_pose(builder, 210, 820)
            builder.move_tracks(0, 18, beat * 0.55)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 16, 82, 210)
            dance_arm_pose(builder, 320, 705)
            builder.move_tracks(0, -18, beat * 0.55)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 12, 22, 182)
            dance_arm_pose(builder, 155, 860)
            builder.move_tracks(10, 14, beat * 0.55)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 12, 22, 182)
            dance_arm_pose(builder, 285, 730)
            builder.move_tracks(-10, -14, beat * 0.55)
            builder.wait(beat * 0.55)
        else:
            builder.play_gif('lets-dance.gif')
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            dance_arm_pose(builder, 150, 850)
            builder.move_tracks(12, 0, beat * 0.65)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 30, 72, 205)
            dance_arm_pose(builder, 305, 710)
            dance_door_pulse(builder, position=835, hold=beat * 0.16)
            builder.wait(beat * 0.4)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            dance_arm_pose(builder, 205, 790)
            builder.move_tracks(-12, 0, beat * 0.65)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 30, 28, 184)
            dance_arm_pose(builder, 130, 880)
            builder.wait(beat * 0.5)
        variant += 1

    builder.play_gif('emotion-love.gif')
    dance_head_pose(builder, HEAD_PIVOT_LEFT + 34, 16, 176)
    dance_arm_pose(builder, 330, 695)
    builder.move_tracks(0, 24, beat * 1.05)
    builder.wait(beat)
    dance_head_pose(builder, HEAD_PIVOT_RIGHT - 34, 16, 176)
    dance_arm_pose(builder, 150, 860)
    builder.move_tracks(0, -24, beat * 1.05)
    builder.wait(beat)
    dance_door_pulse(builder, position=860, hold=beat * 0.25)
    builder.wait(beat * 0.45)
    neutral_pose(builder, keep_eyes=True)


def build_showtime_dance_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
    bpm: float,
) -> None:
    """Broad, crowd-facing phrases for singalong-style show cuts."""
    beat = 60.0 / max(92.0, bpm)
    finale_buffer = 6.5

    builder.play_gif('lets-go.gif')
    builder.play_sound(filename)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
    dance_arm_pose(builder, 190, 800)
    builder.wait(beat * 2)

    variant = 0
    while builder.elapsed < max(beat * 4, duration_seconds - finale_buffer):
        phrase = variant % 4
        if phrase == 0:
            builder.play_gif('lets-go.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 26, 18, 174)
            dance_arm_pose(builder, 325, 705)
            builder.move_tracks(0, 22, beat * 0.9)
            builder.wait(beat * 0.85)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 70, 208)
            dance_arm_pose(builder, 165, 840)
            dance_door_pulse(builder, position=835, hold=beat * 0.18)
            builder.wait(beat * 0.35)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 26, 18, 174)
            dance_arm_pose(builder, 120, 885)
            builder.move_tracks(0, -22, beat * 0.9)
            builder.wait(beat * 0.85)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
            builder.wait(beat * 0.35)
        elif phrase == 1:
            builder.play_gif('lets-dance.gif')
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            dance_arm_pose(builder, ARM_LEFT_UP, ARM_RIGHT_UP)
            builder.move_tracks(10, 16, beat * 0.75)
            builder.wait(beat * 0.7)
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 16, 76, 206)
            dance_arm_pose(builder, 240, 760)
            builder.wait(beat * 0.45)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            dance_arm_pose(builder, 210, 790)
            builder.move_tracks(-10, -16, beat * 0.75)
            builder.wait(beat * 0.7)
            dance_door_pulse(builder, position=860, hold=beat * 0.16)
            builder.wait(beat * 0.45)
        elif phrase == 2:
            builder.play_gif('emotion-love.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 24, 22, 182)
            dance_arm_pose(builder, 300, 690)
            builder.move_tracks(10, 0, beat * 0.6)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 24, 22, 182)
            dance_arm_pose(builder, 145, 860)
            builder.move_tracks(-10, 0, beat * 0.6)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 68, 206)
            dance_arm_pose(builder, 230, 760)
            builder.move_tracks(0, 18, beat * 0.5)
            builder.wait(beat * 0.5)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            builder.move_tracks(0, -18, beat * 0.5)
            builder.wait(beat * 0.5)
        else:
            builder.play_gif('lets-go.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 30, 18, 174)
            dance_arm_pose(builder, 340, 720)
            builder.move_tracks(0, 20, beat * 0.55)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 30, 18, 174)
            dance_arm_pose(builder, 170, 850)
            builder.move_tracks(0, -20, beat * 0.55)
            builder.wait(beat * 0.55)
            dance_door_pulse(builder, position=880, hold=beat * 0.14)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 82, 212)
            dance_arm_pose(builder, 230, 770)
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            builder.wait(beat * 0.35)
        variant += 1

    builder.play_gif('lets-dance.gif')
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
    dance_arm_pose(builder, ARM_LEFT_UP, ARM_RIGHT_UP)
    builder.move_tracks(0, 24, beat * 1.0)
    builder.wait(beat)
    builder.move_tracks(0, -24, beat * 1.0)
    builder.wait(beat)
    dance_door_pulse(builder, position=900, hold=beat * 0.25)
    builder.wait(beat * 0.3)
    neutral_pose(builder, keep_eyes=True)


def build_spooky_funk_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
    bpm: float,
) -> None:
    """Sneaky, playful phrases with peeking and cautionary glances."""
    beat = 60.0 / max(88.0, bpm)
    finale_buffer = 6.0

    builder.play_gif('danger.gif')
    builder.play_sound(filename)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_LEFT + 12, 22, 180)
    dance_arm_pose(builder, 155, 835)
    builder.wait(beat * 1.6)

    variant = 0
    while builder.elapsed < max(beat * 4, duration_seconds - finale_buffer):
        phrase = variant % 4
        if phrase == 0:
            builder.play_gif('danger.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 34, 78, 208)
            dance_arm_pose(builder, 135, 845)
            dance_track_move(
                builder,
                linear=-TRACK_LINEAR_DANCE_MEDIUM,
                angular=TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 0.78,
                linear_scale=1.18,
                angular_scale=1.2,
            )
            builder.wait(beat * 0.7)
            dance_door_pulse(builder, position=820, hold=beat * 0.16)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
            builder.wait(beat * 0.35)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 34, 18, 182)
            dance_arm_pose(builder, 255, 730)
            dance_track_move(
                builder,
                linear=TRACK_LINEAR_DANCE_MEDIUM,
                angular=-TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 0.78,
                linear_scale=1.18,
                angular_scale=1.2,
            )
            builder.wait(beat * 0.7)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
            builder.wait(beat * 0.45)
        elif phrase == 1:
            builder.play_gif('ghibli-landscape.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 20, 20, 182)
            dance_arm_pose(builder, 120, 870)
            dance_track_move(
                builder,
                angular=TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 0.64,
                angular_scale=1.12,
            )
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 20, 82, 210)
            dance_arm_pose(builder, 290, 735)
            dance_track_move(
                builder,
                angular=-TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 0.64,
                angular_scale=1.12,
            )
            builder.wait(beat * 0.55)
            dance_door_pulse(builder, position=760, hold=beat * 0.12)
            builder.wait(beat * 0.35)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
            builder.wait(beat * 0.35)
        elif phrase == 2:
            builder.play_gif('danger.gif')
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 172)
            dance_arm_pose(builder, 145, 845)
            dance_track_move(
                builder,
                linear=-TRACK_LINEAR_DANCE_LARGE,
                duration=beat * 0.56,
                linear_scale=1.18,
            )
            builder.wait(beat * 0.45)
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 28, 20, 184)
            dance_arm_pose(builder, 280, 720)
            builder.wait(beat * 0.35)
            dance_track_move(
                builder,
                linear=TRACK_LINEAR_DANCE_LARGE,
                duration=beat * 0.56,
                linear_scale=1.18,
            )
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 72, 206)
            builder.wait(beat * 0.45)
            dance_door_pulse(builder, position=840, hold=beat * 0.14)
            builder.wait(beat * 0.4)
        else:
            builder.play_gif('iris-yellow.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 26, 22, 182)
            dance_arm_pose(builder, 125, 860)
            dance_track_move(
                builder,
                linear=TRACK_LINEAR_DANCE_SMALL,
                angular=TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 0.64,
                linear_scale=1.14,
                angular_scale=1.16,
            )
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 26, 22, 182)
            dance_arm_pose(builder, 255, 740)
            dance_track_move(
                builder,
                linear=-TRACK_LINEAR_DANCE_SMALL,
                angular=-TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 0.64,
                linear_scale=1.14,
                angular_scale=1.16,
            )
            builder.wait(beat * 0.55)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 84, 212)
            dance_arm_pose(builder, 180, 810)
            builder.wait(beat * 0.45)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
            builder.wait(beat * 0.35)
        variant += 1

    builder.play_gif('lets-go.gif')
    dance_head_pose(builder, HEAD_PIVOT_LEFT + 18, 18, 176)
    dance_arm_pose(builder, 130, 845)
    dance_track_move(
        builder,
        angular=TRACK_ANGULAR_DANCE_BROAD,
        duration=beat * 1.02,
        angular_scale=1.15,
    )
    builder.wait(beat * 0.85)
    dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 18, 176)
    dance_arm_pose(builder, 260, 730)
    dance_track_move(
        builder,
        angular=-TRACK_ANGULAR_DANCE_BROAD,
        duration=beat * 1.02,
        angular_scale=1.15,
    )
    builder.wait(beat * 0.85)
    dance_door_pulse(builder, position=860, hold=beat * 0.18)
    builder.wait(beat * 0.25)
    neutral_pose(builder, keep_eyes=True)


def build_robotic_funk_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
    bpm: float,
) -> None:
    """Sharper stop-and-go phrases with clear freezes and mechanical accents."""
    beat = 60.0 / max(104.0, bpm)
    finale_buffer = 6.0

    builder.play_gif('iris-yellow.gif')
    builder.play_sound(filename)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 16, 176)
    dance_arm_pose(builder, 170, 820)
    builder.wait(beat * 2)

    variant = 0
    while builder.elapsed < max(beat * 4, duration_seconds - finale_buffer):
        phrase = variant % 4
        if phrase == 0:
            builder.play_gif('iris-yellow.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 12, 12, 178)
            dance_arm_pose(builder, 305, 730)
            builder.move_tracks(8, 16, beat * 0.42)
            builder.wait(beat * 0.42)
            builder.wait(beat * 0.22)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 12, 82, 210)
            dance_arm_pose(builder, 140, 870)
            builder.move_tracks(-8, -16, beat * 0.42)
            builder.wait(beat * 0.42)
            builder.wait(beat * 0.22)
            dance_door_pulse(builder, position=790, hold=beat * 0.12)
            builder.wait(beat * 0.3)
        elif phrase == 1:
            builder.play_gif('lets-go.gif')
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
            dance_arm_pose(builder, 150, 860)
            builder.move_tracks(0, 22, beat * 0.38)
            builder.wait(beat * 0.38)
            builder.wait(beat * 0.24)
            dance_arm_pose(builder, 300, 710)
            builder.move_tracks(0, -22, beat * 0.38)
            builder.wait(beat * 0.38)
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 18, 78, 206)
            builder.wait(beat * 0.24)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 28, 186)
            dance_arm_pose(builder, 195, 800)
            builder.wait(beat * 0.38)
        elif phrase == 2:
            builder.play_gif('danger.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 18, 16, 178)
            dance_arm_pose(builder, 120, 850)
            builder.move_tracks(10, 0, beat * 0.34)
            builder.wait(beat * 0.34)
            builder.move_tracks(-10, 0, beat * 0.34)
            builder.wait(beat * 0.34)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 84, 210)
            dance_arm_pose(builder, 290, 720)
            builder.wait(beat * 0.28)
            dance_door_pulse(builder, position=845, hold=beat * 0.12)
            builder.wait(beat * 0.32)
        else:
            builder.play_gif('iris-yellow.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 10, 20, 182)
            dance_arm_pose(builder, 320, 700)
            builder.move_tracks(0, 18, beat * 0.35)
            builder.wait(beat * 0.35)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 10, 20, 182)
            dance_arm_pose(builder, 130, 880)
            builder.move_tracks(0, -18, beat * 0.35)
            builder.wait(beat * 0.35)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
            dance_arm_pose(builder, 205, 790)
            builder.wait(beat * 0.3)
            dance_door_pulse(builder, position=780, hold=beat * 0.1)
            builder.wait(beat * 0.3)
        variant += 1

    builder.play_gif('lets-go.gif')
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 174)
    dance_arm_pose(builder, 150, 860)
    builder.move_tracks(0, 20, beat * 0.65)
    builder.wait(beat * 0.6)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 82, 210)
    dance_arm_pose(builder, 300, 720)
    builder.move_tracks(0, -20, beat * 0.65)
    builder.wait(beat * 0.6)
    builder.wait(beat * 0.25)
    neutral_pose(builder, keep_eyes=True)


def build_generic_dance_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
    bpm: float,
    gif: str,
) -> None:
    """Fallback on-robot dance show for soundtrack tracks without a custom choreography."""
    beat = 60.0 / max(72.0, bpm)
    finale_buffer = 6.5

    builder.play_gif(gif or 'lets-dance.gif')
    builder.play_sound(filename)
    builder.move_servo(5, DOOR_CLOSED)
    dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 175)
    dance_arm_pose(builder, 190, 800)
    builder.wait(beat * 2)

    variant = 0
    while builder.elapsed < max(beat * 4, duration_seconds - finale_buffer):
        if variant % 2 == 0:
            builder.play_gif(gif or 'lets-dance.gif')
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 24, 18, 170)
            dance_arm_pose(builder, 250, 760)
            dance_track_move(
                builder,
                angular=TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 1.32,
                angular_scale=1.08,
            )
            builder.wait(beat)
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 70, 205)
            dance_arm_pose(builder, 170, 830)
            builder.wait(beat)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 24, 18, 170)
            dance_arm_pose(builder, 210, 710)
            dance_track_move(
                builder,
                angular=-TRACK_ANGULAR_DANCE_WIDE,
                duration=beat * 1.32,
                angular_scale=1.08,
            )
            builder.wait(beat)
            dance_door_pulse(builder, position=820, hold=beat * 0.22)
            builder.wait(beat * 0.5)
        else:
            builder.play_gif('iris-yellow2.gif')
            dance_head_pose(builder, HEAD_PIVOT_CENTER, 18, 170)
            dance_arm_pose(builder, 275, 715)
            dance_track_move(
                builder,
                linear=TRACK_LINEAR_DANCE_MEDIUM,
                duration=beat * 1.0,
                linear_scale=1.15,
            )
            builder.wait(beat)
            dance_head_pose(builder, HEAD_PIVOT_LEFT + 18, 82, 206)
            dance_arm_pose(builder, 175, 835)
            builder.wait(beat)
            dance_head_pose(builder, HEAD_PIVOT_RIGHT - 18, 32, 182)
            dance_arm_pose(builder, 230, 700)
            dance_track_move(
                builder,
                linear=-TRACK_LINEAR_DANCE_MEDIUM,
                duration=beat * 1.0,
                linear_scale=1.15,
            )
            builder.wait(beat)
            dance_door_pulse(builder, position=790, hold=beat * 0.2)
            builder.wait(beat * 0.55)
        variant += 1

    neutral_pose(builder, keep_eyes=True)


STYLE_SECTION_PHRASES: dict[str, dict[str, tuple[str, ...]]] = {
    'imperial-march': {
        'intro': ('march_command', 'glide_orbit', 'march_command'),
        'groove': ('march_command', 'strut_turn', 'swagger_slide', 'march_command'),
        'build': ('march_command', 'strut_turn', 'whip_snap', 'march_command'),
        'peak': ('march_command', 'lift_drop', 'windmill_arms', 'march_command', 'strut_turn'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('march_command', 'lift_drop', 'march_command'),
    },
    'spooky-funk': {
        'intro': ('spooky_peek', 'glide_orbit', 'groove_pocket'),
        'groove': ('spooky_peek', 'arc_sway', 'groove_pocket', 'spooky_peek', 'call_answer'),
        'build': ('spooky_peek', 'strut_turn', 'whip_snap', 'spooky_peek'),
        'peak': ('spooky_peek', 'bounce_steps', 'strut_turn', 'body_roll', 'lift_drop'),
        'breakdown': ('glide_orbit', 'spooky_peek', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('spooky_peek', 'lift_drop', 'whip_snap'),
    },
    'robotic-funk': {
        'intro': ('robot_hits', 'glide_orbit', 'groove_pocket'),
        'groove': ('robot_hits', 'bounce_steps', 'whip_snap', 'robot_hits', 'groove_pocket'),
        'build': ('robot_hits', 'strut_turn', 'whip_snap', 'windmill_arms'),
        'peak': ('robot_hits', 'lift_drop', 'whip_snap', 'robot_hits', 'windmill_arms'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('robot_hits', 'lift_drop', 'whip_snap'),
    },
    'hiphop': {
        'intro': ('call_answer', 'glide_orbit', 'groove_pocket'),
        'groove': ('bounce_steps', 'call_answer', 'swagger_slide', 'groove_pocket', 'strut_turn'),
        'build': ('call_answer', 'strut_turn', 'bounce_steps', 'whip_snap', 'swagger_slide'),
        'peak': ('strut_turn', 'bounce_steps', 'lift_drop', 'swagger_slide', 'windmill_arms'),
        'breakdown': ('glide_orbit', 'call_answer', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('strut_turn', 'call_answer', 'lift_drop'),
    },
    'dancehall-groove': {
        'intro': ('call_answer', 'arc_sway', 'groove_pocket'),
        'groove': ('bounce_steps', 'arc_sway', 'call_answer', 'body_roll', 'swagger_slide'),
        'build': ('bounce_steps', 'strut_turn', 'swagger_slide', 'windmill_arms'),
        'peak': ('bounce_steps', 'lift_drop', 'strut_turn', 'body_roll', 'windmill_arms'),
        'breakdown': ('glide_orbit', 'arc_sway', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('bounce_steps', 'lift_drop', 'body_roll'),
    },
    'festival-edm': {
        'intro': ('glide_orbit', 'arc_sway', 'groove_pocket'),
        'groove': ('arc_sway', 'strut_turn', 'bounce_steps', 'windmill_arms', 'swagger_slide'),
        'build': ('bounce_steps', 'lift_drop', 'strut_turn', 'windmill_arms', 'body_roll'),
        'peak': ('lift_drop', 'bounce_steps', 'strut_turn', 'windmill_arms', 'whip_snap'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('lift_drop', 'strut_turn', 'windmill_arms'),
    },
    'cosmic-glide': {
        'intro': ('glide_orbit', 'groove_pocket', 'glide_orbit'),
        'groove': ('glide_orbit', 'arc_sway', 'call_answer', 'body_roll', 'groove_pocket'),
        'build': ('arc_sway', 'glide_orbit', 'swagger_slide'),
        'peak': ('strut_turn', 'glide_orbit', 'body_roll', 'arc_sway'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('glide_orbit', 'lift_drop', 'arc_sway'),
    },
    'ambient-glide': {
        'intro': ('glide_orbit', 'groove_pocket', 'glide_orbit'),
        'groove': ('glide_orbit', 'call_answer', 'body_roll', 'groove_pocket'),
        'build': ('arc_sway', 'glide_orbit', 'body_roll'),
        'peak': ('arc_sway', 'glide_orbit', 'body_roll'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('glide_orbit', 'body_roll'),
    },
    'soul-funk': {
        'intro': ('arc_sway', 'call_answer', 'groove_pocket'),
        'groove': ('arc_sway', 'strut_turn', 'call_answer', 'swagger_slide', 'body_roll'),
        'build': ('strut_turn', 'bounce_steps', 'arc_sway', 'swagger_slide'),
        'peak': ('lift_drop', 'strut_turn', 'arc_sway', 'body_roll', 'windmill_arms'),
        'breakdown': ('glide_orbit', 'call_answer', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('lift_drop', 'strut_turn', 'body_roll'),
    },
    'showtime': {
        'intro': ('strut_turn', 'arc_sway', 'groove_pocket'),
        'groove': ('strut_turn', 'call_answer', 'arc_sway', 'swagger_slide', 'windmill_arms'),
        'build': ('lift_drop', 'strut_turn', 'swagger_slide', 'windmill_arms'),
        'peak': ('lift_drop', 'strut_turn', 'bounce_steps', 'windmill_arms', 'whip_snap'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('lift_drop', 'strut_turn', 'windmill_arms'),
    },
    'disco': {
        'intro': ('arc_sway', 'strut_turn', 'groove_pocket'),
        'groove': ('arc_sway', 'strut_turn', 'call_answer', 'swagger_slide', 'body_roll'),
        'build': ('strut_turn', 'bounce_steps', 'swagger_slide', 'windmill_arms'),
        'peak': ('lift_drop', 'strut_turn', 'arc_sway', 'windmill_arms', 'whip_snap'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('lift_drop', 'arc_sway', 'strut_turn'),
    },
    'pulse': {
        'intro': ('arc_sway', 'glide_orbit', 'groove_pocket'),
        'groove': ('arc_sway', 'strut_turn', 'bounce_steps', 'swagger_slide', 'call_answer'),
        'build': ('bounce_steps', 'strut_turn', 'windmill_arms', 'swagger_slide'),
        'peak': ('lift_drop', 'strut_turn', 'bounce_steps', 'windmill_arms', 'whip_snap'),
        'breakdown': ('glide_orbit', 'groove_pocket'),
        'breath': ('glide_orbit', 'groove_pocket'),
        'finale': ('lift_drop', 'strut_turn', 'windmill_arms'),
    },
}


def style_gif_cycle(style: str, default_gif: str) -> tuple[str, ...]:
    if style == 'imperial-march':
        return ('danger.gif', 'iris-yellow.gif', 'lets-go.gif')
    if style == 'spooky-funk':
        return ('danger.gif', 'ghibli-landscape.gif', 'iris-yellow.gif')
    if style == 'robotic-funk':
        return ('iris-yellow.gif', 'lets-go.gif', 'danger.gif')
    if style in {'cosmic-glide', 'ambient-glide'}:
        return ('ghibli-landscape.gif', 'iris-yellow2.gif', 'realistic-orange.gif')
    if style in {'hiphop', 'dancehall-groove'}:
        return ('lets-go.gif', 'realistic-orange.gif', 'iris-yellow2.gif')
    return (default_gif, 'lets-go.gif', 'lets-dance.gif')


def style_min_bpm(style: str) -> float:
    if style == 'imperial-march':
        return 88.0
    if style in {'ambient-glide', 'cosmic-glide'}:
        return 82.0
    if style == 'hiphop':
        return 84.0
    if style == 'dancehall-groove':
        return 96.0
    if style == 'festival-edm':
        return 104.0
    if style == 'robotic-funk':
        return 108.0
    return 92.0


def style_opening_pose(builder: SequenceBuilder, *, style: str, beat: float, gif: str) -> None:
    builder.play_gif(gif)
    builder.move_servo(5, DOOR_CLOSED)

    if style == 'imperial-march':
        dance_head_levels(builder, 0.0, 0.12, 0.12)
        dance_arm_levels(builder, 0.56, 0.56)
        builder.wait(beat * 2.0)
        return

    if style in {'cosmic-glide', 'ambient-glide'}:
        dance_head_levels(builder, -0.16, 0.18, 0.14)
        dance_arm_levels(builder, 0.48, 0.48)
        builder.wait(beat * 1.8)
        return

    if style in {'robotic-funk', 'hiphop'}:
        dance_head_levels(builder, 0.0, 0.12, 0.16)
        dance_arm_levels(builder, 0.58, 0.58)
        builder.wait(beat * 1.8)
        return

    dance_head_levels(builder, 0.0, 0.16, 0.16)
    dance_arm_levels(builder, 0.6, 0.6)
    builder.wait(beat * 1.8)


def phrase_arc_sway(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
    dramatic: float = 1.0,
) -> float:
    start = builder.elapsed
    arm_lead = 0.72 + (intensity * 0.22)
    arm_follow = 0.34 + (intensity * 0.12)
    center_lift = 0.54 + (intensity * 0.18)
    head_lift = 0.18 + (intensity * 0.24)
    turn = round((14 + (intensity * 16)) * dramatic)
    linear = round((8 + (intensity * 10)) * dramatic)

    builder.play_gif(gif)
    dance_head_levels(builder, -0.5 * direction, head_lift, 0.1 + (head_lift * 0.4))
    if direction < 0:
        dance_arm_levels(builder, arm_lead, arm_follow)
    else:
        dance_arm_levels(builder, arm_follow, arm_lead)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 0.8)
    builder.wait(beat * 0.74)

    dance_head_levels(builder, 0.0, 0.64, 0.64)
    dance_arm_levels(builder, center_lift, center_lift)
    builder.wait(beat * 0.42)

    dance_head_levels(builder, 0.5 * direction, 0.1 + (head_lift * 0.4), head_lift)
    if direction < 0:
        dance_arm_levels(builder, arm_follow, arm_lead)
    else:
        dance_arm_levels(builder, arm_lead, arm_follow)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 0.8)
    builder.wait(beat * 0.74)

    dance_head_levels(builder, 0.0, 0.26, 0.26)
    dance_arm_levels(builder, 0.52, 0.56)
    builder.wait(beat * 0.36)
    return builder.elapsed - start


def phrase_strut_turn(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
    swagger: float = 1.0,
) -> float:
    start = builder.elapsed
    lead_arm = 0.84 + (intensity * 0.12)
    counter_arm = 0.3 + (intensity * 0.16)
    center_arm = 0.58 + (intensity * 0.22)
    turn = round((18 + (intensity * 22)) * swagger)
    linear = round((10 + (intensity * 12)) * swagger)

    builder.play_gif(gif)
    dance_head_levels(builder, -0.36 * direction, 0.16, 0.14)
    if direction < 0:
        dance_arm_levels(builder, lead_arm, counter_arm)
    else:
        dance_arm_levels(builder, counter_arm, lead_arm)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 0.9)
    builder.wait(beat * 0.78)

    dance_head_levels(builder, 0.0, 0.72, 0.72)
    dance_arm_levels(builder, center_arm, center_arm)
    builder.wait(beat * 0.36)

    dance_head_levels(builder, 0.36 * direction, 0.16, 0.14)
    if direction < 0:
        dance_arm_levels(builder, counter_arm, lead_arm)
    else:
        dance_arm_levels(builder, lead_arm, counter_arm)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 0.9)
    builder.wait(beat * 0.78)

    dance_door_pulse(builder, position=round(lerp(790, 860, intensity)), hold=beat * 0.14)
    builder.wait(beat * 0.28)
    return builder.elapsed - start


def phrase_glide_orbit(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
    airy: float = 1.0,
) -> float:
    start = builder.elapsed
    turn = round((12 + (intensity * 18)) * airy)
    linear = round((6 + (intensity * 8)) * airy)

    builder.play_gif(gif)
    dance_head_levels(builder, -0.26 * direction, 0.26, 0.2)
    if direction < 0:
        dance_arm_levels(builder, 0.42, 0.6)
    else:
        dance_arm_levels(builder, 0.6, 0.42)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 1.3)
    builder.wait(beat * 1.2)

    dance_head_levels(builder, 0.0, 0.36, 0.34)
    dance_arm_levels(builder, 0.5, 0.5)
    builder.wait(beat * 0.42)

    dance_head_levels(builder, 0.26 * direction, 0.2, 0.26)
    if direction < 0:
        dance_arm_levels(builder, 0.58, 0.42)
    else:
        dance_arm_levels(builder, 0.42, 0.58)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 1.3)
    builder.wait(beat * 1.2)

    builder.wait(beat * 0.3)
    return builder.elapsed - start


def phrase_bounce_steps(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    start = builder.elapsed
    travel = round(6 + (intensity * 10))
    turn = round(10 + (intensity * 14))

    builder.play_gif(gif)
    for step_index in range(4):
        phase_direction = direction if step_index % 2 == 0 else -direction
        head_offset = 0.18 * phase_direction
        left_level = 0.32 + (0.5 if step_index % 2 == 0 else 0.16)
        right_level = 0.32 + (0.5 if step_index % 2 == 1 else 0.16)
        dance_head_levels(builder, head_offset, 0.18 + (0.52 if step_index % 2 == 0 else 0.14), 0.18 + (0.52 if step_index % 2 == 1 else 0.14))
        dance_arm_levels(builder, left_level, right_level)
        dance_track_move(
            builder,
            linear=travel * phase_direction,
            angular=(turn if step_index < 2 else -turn) * phase_direction,
            duration=beat * 0.36,
        )
        builder.wait(beat * 0.34)
        builder.wait(beat * 0.08)

    dance_door_pulse(builder, position=round(lerp(780, 850, intensity)), hold=beat * 0.1)
    builder.wait(beat * 0.18)
    return builder.elapsed - start


def phrase_robot_hits(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    start = builder.elapsed
    turn = round(14 + (intensity * 14))
    linear = round(6 + (intensity * 8))

    builder.play_gif(gif)
    dance_head_levels(builder, -0.14 * direction, 0.16, 0.18)
    dance_arm_levels(builder, 0.82 if direction < 0 else 0.32, 0.32 if direction < 0 else 0.82)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 0.34)
    builder.wait(beat * 0.32)
    builder.wait(beat * 0.18)

    dance_head_levels(builder, 0.14 * direction, 0.72, 0.72)
    dance_arm_levels(builder, 0.46, 0.46)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 0.34)
    builder.wait(beat * 0.32)
    builder.wait(beat * 0.18)

    dance_head_levels(builder, 0.0, 0.2, 0.2)
    dance_arm_levels(builder, 0.22 if direction < 0 else 0.78, 0.78 if direction < 0 else 0.22)
    dance_door_pulse(builder, position=round(lerp(760, 840, intensity)), hold=beat * 0.08)
    builder.wait(beat * 0.36)
    builder.wait(beat * 0.2)
    return builder.elapsed - start


def phrase_march_command(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    start = builder.elapsed
    linear = round(12 + (intensity * 12))
    turn = round(18 + (intensity * 16))

    builder.play_gif(gif)
    dance_head_levels(builder, -0.22 * direction, 0.12, 0.12)
    if direction < 0:
        dance_arm_levels(builder, 0.32, 0.86)
    else:
        dance_arm_levels(builder, 0.86, 0.32)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 0.72)
    builder.wait(beat * 0.7)

    dance_head_levels(builder, 0.0, 0.18, 0.18)
    if direction < 0:
        dance_arm_levels(builder, 0.4, 0.82)
    else:
        dance_arm_levels(builder, 0.82, 0.4)
    builder.wait(beat * 0.35)

    dance_head_levels(builder, 0.22 * direction, 0.12, 0.12)
    if direction < 0:
        dance_arm_levels(builder, 0.26, 0.74)
    else:
        dance_arm_levels(builder, 0.74, 0.26)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 0.72)
    builder.wait(beat * 0.7)

    dance_door_pulse(builder, position=round(lerp(780, 830, intensity)), hold=beat * 0.12)
    builder.wait(beat * 0.28)
    return builder.elapsed - start


def phrase_spooky_peek(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    start = builder.elapsed
    linear = round(12 + (intensity * 12))
    turn = round(18 + (intensity * 14))

    builder.play_gif(gif)
    dance_head_levels(builder, -0.4 * direction, 0.62, 0.18)
    dance_arm_levels(builder, 0.24, 0.74)
    dance_track_move(builder, linear=-linear * direction, angular=turn * direction, duration=beat * 0.66)
    builder.wait(beat * 0.6)

    dance_door_pulse(builder, position=round(lerp(800, 860, intensity)), hold=beat * 0.1)
    builder.wait(beat * 0.2)

    dance_head_levels(builder, 0.38 * direction, 0.18, 0.62)
    dance_arm_levels(builder, 0.72, 0.26)
    dance_track_move(builder, linear=linear * direction, angular=-turn * direction, duration=beat * 0.66)
    builder.wait(beat * 0.6)

    dance_head_levels(builder, 0.0, 0.22, 0.22)
    dance_arm_levels(builder, 0.4, 0.54)
    builder.wait(beat * 0.36)
    return builder.elapsed - start


def phrase_call_answer(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    start = builder.elapsed
    turn = round(10 + (intensity * 10))
    linear = round(6 + (intensity * 8))

    builder.play_gif(gif)
    dance_head_levels(builder, -0.32 * direction, 0.22, 0.16)
    if direction < 0:
        dance_arm_levels(builder, 0.9, 0.28)
    else:
        dance_arm_levels(builder, 0.28, 0.9)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 0.54)
    builder.wait(beat * 0.48)

    dance_head_levels(builder, 0.0, 0.44, 0.44)
    dance_arm_levels(builder, 0.52, 0.52)
    builder.wait(beat * 0.24)

    dance_head_levels(builder, 0.32 * direction, 0.16, 0.22)
    if direction < 0:
        dance_arm_levels(builder, 0.24, 0.78)
    else:
        dance_arm_levels(builder, 0.78, 0.24)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 0.54)
    builder.wait(beat * 0.48)

    dance_head_levels(builder, 0.0, 0.7, 0.7)
    dance_arm_levels(builder, 0.62, 0.74)
    builder.wait(beat * 0.3)
    return builder.elapsed - start


def phrase_lift_drop(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    start = builder.elapsed
    turn = round(18 + (intensity * 18))
    linear = round(8 + (intensity * 10))

    builder.play_gif(gif)
    dance_head_levels(builder, 0.0, 0.74, 0.74)
    dance_arm_levels(builder, 1.0, 1.0)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 0.62)
    builder.wait(beat * 0.58)

    dance_door_pulse(builder, position=round(lerp(820, 900, intensity)), hold=beat * 0.12)
    builder.wait(beat * 0.2)

    dance_head_levels(builder, -0.18 * direction, 0.2, 0.2)
    dance_arm_levels(builder, 0.57, 0.57)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 0.62)
    builder.wait(beat * 0.58)

    dance_head_levels(builder, 0.0, 0.16, 0.16)
    dance_arm_levels(builder, 0.41, 0.41)
    builder.wait(beat * 0.34)
    return builder.elapsed - start


def phrase_swagger_slide(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    """Confident side-slide with one arm leading high."""
    start = builder.elapsed
    lead = 0.86 + (intensity * 0.12)
    counter = 0.22 + (intensity * 0.1)
    linear = round(10 + (intensity * 10))
    turn = round(10 + (intensity * 14))

    builder.play_gif(gif)
    dance_head_levels(builder, -0.44 * direction, 0.14, 0.12)
    if direction < 0:
        dance_arm_levels(builder, lead, counter)
    else:
        dance_arm_levels(builder, counter, lead)
    dance_track_move(builder, linear=linear * direction, angular=turn * direction, duration=beat * 1.05)
    builder.wait(beat * 0.88)

    dance_head_levels(builder, 0.0, 0.62, 0.62)
    dance_arm_levels(builder, 0.58, 0.58)
    builder.wait(beat * 0.22)

    dance_head_levels(builder, 0.44 * direction, 0.12, 0.14)
    if direction < 0:
        dance_arm_levels(builder, counter, lead)
    else:
        dance_arm_levels(builder, lead, counter)
    dance_track_move(builder, linear=-linear * direction, angular=-turn * direction, duration=beat * 1.05)
    builder.wait(beat * 0.88)

    dance_door_pulse(builder, position=round(lerp(805, 870, intensity)), hold=beat * 0.14)
    builder.wait(beat * 0.26)
    return builder.elapsed - start


def phrase_whip_snap(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    """Sharp staccato hits with head whips - punchy feel."""
    start = builder.elapsed
    turn = round(12 + (intensity * 12))

    builder.play_gif(gif)
    dance_head_levels(builder, -0.55 * direction, 0.78, 0.14)
    dance_arm_levels(builder, 0.85, 0.25)
    dance_track_move(builder, angular=turn * direction, duration=beat * 0.36)
    builder.wait(beat * 0.32)
    builder.wait(beat * 0.16)

    dance_head_levels(builder, 0.55 * direction, 0.14, 0.78)
    dance_arm_levels(builder, 0.25, 0.85)
    dance_track_move(builder, angular=-turn * direction, duration=beat * 0.36)
    builder.wait(beat * 0.32)
    builder.wait(beat * 0.16)

    dance_head_levels(builder, 0.0, 0.44, 0.44)
    dance_arm_levels(builder, 0.55, 0.55)
    dance_door_pulse(builder, position=round(lerp(790, 850, intensity)), hold=beat * 0.1)
    builder.wait(beat * 0.28)
    return builder.elapsed - start


def phrase_groove_pocket(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    """Smaller, locked-in pocket groove - less travel, more feel."""
    start = builder.elapsed
    arm_a = 0.62 + (intensity * 0.14)
    arm_b = 0.38 + (intensity * 0.1)
    head_bob = 0.52 + (intensity * 0.2)
    travel = round(4 + (intensity * 6))

    builder.play_gif(gif)
    for step in range(3):
        d = direction if step % 2 == 0 else -direction
        dance_head_levels(
            builder,
            -0.18 * d,
            head_bob if step % 2 == 0 else 0.2,
            0.2 if step % 2 == 0 else head_bob,
        )
        if d < 0:
            dance_arm_levels(builder, arm_a, arm_b)
        else:
            dance_arm_levels(builder, arm_b, arm_a)
        dance_track_move(builder, linear=travel * d, angular=(8 * d), duration=beat * 0.42)
        builder.wait(beat * 0.38)
        builder.wait(beat * 0.1)

    dance_head_levels(builder, 0.0, 0.28, 0.28)
    dance_arm_levels(builder, 0.48, 0.52)
    builder.wait(beat * 0.24)
    return builder.elapsed - start


def phrase_body_roll(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    """Sequential wave through head-arms-door simulating a body roll."""
    start = builder.elapsed
    roll_speed = beat * 0.28

    builder.play_gif(gif)
    dance_head_levels(builder, -0.22 * direction, 0.82, 0.82)
    dance_arm_levels(builder, 0.3, 0.3)
    builder.wait(roll_speed)

    dance_head_levels(builder, 0.0, 0.4, 0.4)
    dance_arm_levels(builder, 0.88, 0.88)
    builder.wait(roll_speed)

    dance_arm_levels(builder, 0.5, 0.5)
    dance_door_pulse(builder, position=round(lerp(830, 900, intensity)), hold=roll_speed)
    dance_head_levels(builder, 0.22 * direction, 0.18, 0.18)
    builder.wait(roll_speed)

    dance_head_levels(builder, 0.22 * direction, 0.82, 0.82)
    dance_arm_levels(builder, 0.3, 0.3)
    builder.wait(roll_speed)

    dance_head_levels(builder, 0.0, 0.4, 0.4)
    dance_arm_levels(builder, 0.82, 0.82)
    builder.wait(roll_speed)

    dance_arm_levels(builder, 0.48, 0.48)
    dance_head_levels(builder, 0.0, 0.26, 0.26)
    builder.wait(beat * 0.2)
    return builder.elapsed - start


def phrase_windmill_arms(
    builder: SequenceBuilder,
    *,
    beat: float,
    intensity: float,
    direction: int,
    gif: str,
) -> float:
    """Alternating arm pumps with head tracking - energetic feel."""
    start = builder.elapsed
    high = 0.9 + (intensity * 0.1)
    low = 0.15 + (intensity * 0.08)
    turn = round(8 + (intensity * 10))

    builder.play_gif(gif)
    for pump in range(4):
        left_high = pump % 2 == 0
        dance_arm_levels(builder, high if left_high else low, low if left_high else high)
        d = direction if left_high else -direction
        dance_head_levels(
            builder,
            -0.28 * d,
            0.22 if pump % 2 == 0 else 0.58,
            0.58 if pump % 2 == 0 else 0.22,
        )
        dance_track_move(builder, angular=turn * d, duration=beat * 0.36)
        builder.wait(beat * 0.33)

    dance_arm_levels(builder, 0.5, 0.5)
    dance_head_levels(builder, 0.0, 0.32, 0.32)
    dance_door_pulse(builder, position=round(lerp(800, 860, intensity)), hold=beat * 0.12)
    builder.wait(beat * 0.22)
    return builder.elapsed - start


PHRASE_BUILDERS = {
    'arc_sway': phrase_arc_sway,
    'strut_turn': phrase_strut_turn,
    'glide_orbit': phrase_glide_orbit,
    'bounce_steps': phrase_bounce_steps,
    'robot_hits': phrase_robot_hits,
    'march_command': phrase_march_command,
    'spooky_peek': phrase_spooky_peek,
    'call_answer': phrase_call_answer,
    'lift_drop': phrase_lift_drop,
    'swagger_slide': phrase_swagger_slide,
    'whip_snap': phrase_whip_snap,
    'groove_pocket': phrase_groove_pocket,
    'body_roll': phrase_body_roll,
    'windmill_arms': phrase_windmill_arms,
}


def normalized_analysis_sections(duration_seconds: float, analysis: dict[str, Any] | None, beat: float) -> list[dict[str, Any]]:
    if analysis and analysis.get('sections'):
        sections = [
            section
            for section in analysis.get('sections', [])
            if float(section.get('duration') or 0.0) > 0.2
        ]
        if sections:
            return sections

    section_duration = clamp_float(beat * 16.0, 7.5, 13.0)
    cursor = 0.0
    sections: list[dict[str, Any]] = []
    while cursor < duration_seconds:
        section_end = min(duration_seconds, cursor + section_duration)
        role = 'groove'
        if not sections:
            role = 'intro'
        elif section_end >= duration_seconds:
            role = 'finale'
        sections.append({
            'start': round(cursor, 3),
            'end': round(section_end, 3),
            'duration': round(section_end - cursor, 3),
            'energy': 0.58,
            'peak_energy': 0.72,
            'accent_density': 0.7,
            'accent_count': 4,
            'role': role,
            'trend': 'steady',
        })
        cursor = section_end
    return sections


def run_style_section(
    builder: SequenceBuilder,
    *,
    style: str,
    beat: float,
    section: dict[str, Any],
    base_energy: float,
    gif_cycle: tuple[str, ...],
    index: int,
    ctx: DanceContext | None = None,
    song_offset: float = 0.0,
) -> None:
    role = str(section.get('role') or 'groove')
    section_duration = max(beat * 2.2, float(section.get('duration') or 0.0))
    section_start_song = float(section.get('start') or 0.0)
    section_end_song = float(section.get('end') or section_start_song + section_duration)
    base_intensity = dance_section_intensity(section, base_energy)
    phrase_names = STYLE_SECTION_PHRASES.get(style, STYLE_SECTION_PHRASES['pulse']).get(
        role,
        STYLE_SECTION_PHRASES.get(style, STYLE_SECTION_PHRASES['pulse'])['groove'],
    )

    section_accents = ctx.accents_between(section_start_song, section_end_song) if ctx else []
    target_end = builder.elapsed + section_duration
    phrase_index = 0
    section_start_elapsed = builder.elapsed

    while builder.elapsed + (beat * 1.4) < target_end:
        progress = clamp_float(
            (builder.elapsed - section_start_elapsed) / max(1.0, section_duration), 0.0, 1.0
        )

        if ctx:
            intensity = ctx.ramped_intensity(base_intensity, progress, role)
        else:
            intensity = base_intensity

        # Highlight opportunity at peak/build moments past the opening
        if ctx and phrase_index > 0 and progress > 0.35 and ctx.should_highlight(role, intensity):
            highlight = ctx.pick([
                highlight_both_arms_up, highlight_freeze,
                highlight_spin_burst, highlight_door_drama,
            ])
            highlight(builder, ctx, beat, intensity)
            phrase_index += 1
            continue

        if ctx:
            phrase_name = ctx.next_phrase(phrase_names)
            direction = ctx.direction_for(index + phrase_index)
        else:
            phrase_name = phrase_names[(index + phrase_index) % len(phrase_names)]
            direction = -1 if (index + phrase_index) % 2 == 0 else 1

        phrase_builder = PHRASE_BUILDERS[phrase_name]
        gif = gif_cycle[(index + phrase_index) % len(gif_cycle)]
        phrase_builder(
            builder,
            beat=beat,
            intensity=intensity,
            direction=direction,
            gif=gif,
        )

        # Insert accent hit if there's a nearby accent in the song
        if ctx and section_accents:
            current_song_time = builder.elapsed - song_offset
            upcoming = [t for t in section_accents if 0.0 < (t - current_song_time) < beat * 1.2]
            if upcoming and ctx.should_accent_hit(builder.elapsed, beat):
                if builder.elapsed + (beat * 0.6) < target_end:
                    accent_hit(builder, ctx, intensity)

        phrase_index += 1

    spare = target_end - builder.elapsed
    if ctx and spare > 0.15:
        transition_breath(builder, ctx, beat)
    elif spare > 0.12:
        builder.wait(min(spare, beat * 0.45))


def build_style_finale(
    builder: SequenceBuilder,
    *,
    style: str,
    beat: float,
    intensity: float,
    gif_cycle: tuple[str, ...],
) -> None:
    if style == 'imperial-march':
        phrase_march_command(builder, beat=beat, intensity=intensity, direction=-1, gif=gif_cycle[0])
        phrase_lift_drop(builder, beat=beat, intensity=intensity, direction=1, gif=gif_cycle[1 % len(gif_cycle)])
        return

    if style == 'spooky-funk':
        phrase_spooky_peek(builder, beat=beat, intensity=intensity, direction=-1, gif=gif_cycle[0])
        phrase_lift_drop(builder, beat=beat, intensity=intensity, direction=1, gif=gif_cycle[1 % len(gif_cycle)])
        return

    if style in {'ambient-glide', 'cosmic-glide'}:
        phrase_glide_orbit(builder, beat=beat, intensity=intensity, direction=-1, gif=gif_cycle[0], airy=1.1)
        phrase_arc_sway(builder, beat=beat, intensity=max(0.28, intensity - 0.12), direction=1, gif=gif_cycle[1 % len(gif_cycle)], dramatic=0.85)
        return

    if style in {'hiphop', 'dancehall-groove'}:
        phrase_call_answer(builder, beat=beat, intensity=intensity, direction=-1, gif=gif_cycle[0])
        phrase_strut_turn(builder, beat=beat, intensity=intensity, direction=1, gif=gif_cycle[1 % len(gif_cycle)], swagger=1.08)
        return

    if style == 'robotic-funk':
        phrase_robot_hits(builder, beat=beat, intensity=intensity, direction=-1, gif=gif_cycle[0])
        phrase_lift_drop(builder, beat=beat, intensity=intensity, direction=1, gif=gif_cycle[1 % len(gif_cycle)])
        return

    phrase_lift_drop(builder, beat=beat, intensity=intensity, direction=-1, gif=gif_cycle[0])
    phrase_strut_turn(builder, beat=beat, intensity=intensity, direction=1, gif=gif_cycle[1 % len(gif_cycle)], swagger=1.06)


def build_adaptive_dance_show(
    builder: SequenceBuilder,
    *,
    filename: str,
    duration_seconds: float,
    style: str,
    bpm: float,
    gif: str,
    base_energy: float,
    analysis: dict[str, Any] | None,
) -> None:
    effective_bpm = bpm or (float(analysis.get('estimated_bpm') or 0.0) if analysis else 0.0)
    beat = 60.0 / max(style_min_bpm(style), effective_bpm)
    gif_cycle = style_gif_cycle(style, gif)
    sections = normalized_analysis_sections(duration_seconds, analysis, beat)
    accent_times = list(analysis.get('accent_times') or []) if analysis else []

    seed = f'{filename}:{style}:{bpm}'
    ctx = DanceContext(seed=seed, accent_times=accent_times)

    builder.play_sound(filename)
    song_offset = builder.elapsed
    ctx.song_offset = song_offset

    style_opening_pose(builder, style=style, beat=beat, gif=gif_cycle[0])

    for index, section in enumerate(sections):
        if str(section.get('role') or '') == 'finale':
            continue

        if index > 0 and builder.elapsed + beat * 0.5 < song_offset + duration_seconds:
            transition_breath(builder, ctx, beat)

        run_style_section(
            builder,
            style=style,
            beat=beat,
            section=section,
            base_energy=base_energy,
            gif_cycle=gif_cycle,
            index=index,
            ctx=ctx,
            song_offset=song_offset,
        )

    final_section = next(
        (section for section in reversed(sections) if str(section.get('role') or '') == 'finale'),
        sections[-1] if sections else {'energy': base_energy, 'accent_density': 0.8, 'role': 'finale'},
    )
    build_style_finale(
        builder,
        style=style,
        beat=beat,
        intensity=dance_section_intensity(final_section, base_energy),
        gif_cycle=gif_cycle,
    )
    neutral_pose(builder, keep_eyes=True)


def build_dance_plan(track_payload: dict[str, Any]) -> tuple[str, list[PlanStep]] | None:
    """Build a fully local dance show plan from a UI-selected track."""
    if not isinstance(track_payload, dict):
        return None

    filename = track_payload.get('filename')
    if not isinstance(filename, str) or not filename:
        return None

    track_id = str(track_payload.get('id') or DANCE_DEFAULT_TRACK_ID)
    duration_ms = int(track_payload.get('duration_ms') or 0)
    duration_seconds = max(8.0, duration_ms / 1000.0)
    style = str(track_payload.get('style') or '')
    bpm = float(track_payload.get('bpm') or 108.0)
    gif = str(track_payload.get('gif') or 'lets-dance.gif')
    base_energy = float(track_payload.get('energy') or 0.62)
    analysis_payload = track_payload.get('analysis') if isinstance(track_payload.get('analysis'), dict) else None
    analysis = analysis_payload or load_soundtrack_analysis(filename, fallback_bpm=bpm)
    effective_duration = max(
        duration_seconds,
        float(analysis.get('duration_seconds') or 0.0) if analysis else 0.0,
    )

    builder = SequenceBuilder()
    builder.stop_sound()
    builder.stop_tracks()

    if style == 'define-dancing' or track_id == '22-define-dancing-from-wall-e-score':
        build_define_dancing_show(
            builder,
            filename=filename,
            duration_seconds=effective_duration,
        )
    else:
        resolved_style = style or ('imperial-march' if 'imperial-march' in track_id else 'pulse')
        build_adaptive_dance_show(
            builder,
            filename=filename,
            duration_seconds=effective_duration,
            style=resolved_style,
            bpm=bpm,
            gif=gif,
            base_energy=base_energy,
            analysis=analysis,
        )

    return f'dance:{track_id}', builder.build()



def build_sequence_plan(seq_id: str) -> list[PlanStep] | None:
    builder = SequenceBuilder()
    builder.stop_sound()
    builder.stop_tracks()

    if seq_id == 'hands-up':
        build_hands_up(builder)
    elif seq_id == 'candy':
        build_candy(builder)
    elif seq_id == 'party':
        build_party(builder)
    elif seq_id == 'neutral':
        neutral_pose(builder, close_door=True, keep_eyes=False)
    elif seq_id == 'wave-hello':
        build_wave_hello(builder)
    elif seq_id == 'curious-scan':
        build_curious_scan(builder)
    elif seq_id == 'peekaboo':
        build_peekaboo(builder)
    elif seq_id == 'spin-wiggle':
        build_spin_wiggle(builder)
    elif seq_id == 'double-take':
        build_double_take(builder)
    elif seq_id == 'shimmy':
        build_shimmy(builder)
    elif seq_id == 'pirouette':
        build_pirouette(builder)
    elif seq_id == 'suche':
        build_suche(builder)
    elif seq_id == 'idle-listen':
        build_idle_listen(builder)
    elif seq_id == 'idle-peek':
        build_idle_peek(builder)
    elif seq_id == 'idle-fidget':
        build_idle_fidget(builder)
    else:
        return None

    return builder.build()


class SequenceScheduler:
    def __init__(self, *, clock=time.monotonic) -> None:
        self._clock = clock
        self._active: ActiveSequence | None = None

    @property
    def active_sequence_id(self) -> str | None:
        if self._active is None:
            return None
        return self._active.seq_id

    def _emit_sequence_state(self, node: OutputNode, seq_id: str, active: bool) -> None:
        node.send_output('sequence_state', pa.array([{'id': seq_id, 'active': active}]), metadata={})

    def request_sequence(self, node: OutputNode, seq_id: str) -> bool:
        steps = build_sequence_plan(seq_id)
        if steps is None:
            return False

        previous = self.active_sequence_id
        if previous:
            print(f'Sequence: interrupt -> {previous} -> {seq_id}')
        else:
            print(f'Sequence: trigger -> {seq_id}')

        self._active = ActiveSequence(seq_id=seq_id, started_at=self._clock(), steps=steps)
        self._emit_sequence_state(node, seq_id, True)
        self.emit_due_steps(node)
        return True

    def request_dance(self, node: OutputNode, track_payload: dict[str, Any]) -> bool:
        plan = build_dance_plan(track_payload)
        if plan is None:
            return False

        seq_id, steps = plan
        previous = self.active_sequence_id
        if previous:
            print(f'Sequence: interrupt -> {previous} -> {seq_id}')
        else:
            print(f'Sequence: trigger -> {seq_id}')

        self._active = ActiveSequence(seq_id=seq_id, started_at=self._clock(), steps=steps)
        self._emit_sequence_state(node, seq_id, True)
        self.emit_due_steps(node)
        return True

    def cancel_active(self, node: OutputNode, *, reason: str = 'cancel') -> bool:
        if self._active is None:
            return False

        seq_id = self._active.seq_id
        print(f'Sequence: {reason} -> {seq_id}')
        self._active = None
        node.send_output('stop_sequence', pa.array([]), metadata={})
        node.send_output(
            'move_tracks_sequence',
            pa.array([{'linear': 0, 'angular': 0, 'duration': 0.0}]),
            metadata={},
        )
        self._emit_sequence_state(node, seq_id, False)
        return True

    def emit_due_steps(self, node: OutputNode) -> None:
        if self._active is None:
            return

        elapsed = self._clock() - self._active.started_at
        while self._active.next_step_index < len(self._active.steps):
            step = self._active.steps[self._active.next_step_index]
            if step.at > elapsed + 1e-9:
                break
            node.send_output(step.output_id, pa.array(step.payload), metadata={})
            self._active.next_step_index += 1

        if self._active.next_step_index >= len(self._active.steps):
            seq_id = self._active.seq_id
            print(f'Sequence: {seq_id} complete')
            self._active = None
            self._emit_sequence_state(node, seq_id, False)
