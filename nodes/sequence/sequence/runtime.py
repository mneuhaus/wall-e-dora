from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Protocol

import pyarrow as pa

# Neutral/default positions (tune as needed)
# Arms (position values provided by user)
ARM_LEFT_NEUTRAL = 0      # servo #2 (down)
ARM_LEFT_UP = 350         # servo #2 (up)
ARM_RIGHT_NEUTRAL = 940   # servo #13 (down)
ARM_RIGHT_UP = 640        # servo #13 (up)
# Head sides (position values provided by user)
HEAD_LEFT_NEUTRAL = 0     # servo #6 (down)
HEAD_LEFT_UP = 120        # servo #6 (up)
HEAD_RIGHT_NEUTRAL = 200  # servo #4 (down)
HEAD_RIGHT_UP = 85        # servo #4 (up)
# Head pivot (position values provided by user)
HEAD_PIVOT_LEFT = 433     # servo #14 (left)
HEAD_PIVOT_RIGHT = 580    # servo #14 (right)
HEAD_PIVOT_CENTER = 500   # servo #14 (center)
DOOR_CLOSED = 700         # servo #5 (matches UI toggle expectations)
DOOR_OPEN = 1023          # servo #5 (fully open)
DEFAULT_EYES = 'realistic-orange.gif'
TRACK_TURN_FAST = 68
TRACK_TURN_MEDIUM = 54
TRACK_TURN_SHIMMY = 38


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

    def cancel_active(self, node: OutputNode, *, reason: str = 'cancel') -> bool:
        if self._active is None:
            return False

        seq_id = self._active.seq_id
        print(f'Sequence: {reason} -> {seq_id}')
        self._active = None
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
