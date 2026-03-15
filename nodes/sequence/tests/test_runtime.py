from sequence.runtime import (
    ARM_LEFT_NEUTRAL,
    ARM_LEFT_UP,
    HEAD_RIGHT_NEUTRAL,
    HEAD_RIGHT_UP,
    SequenceScheduler,
    amplify_left_dance_arm_position,
    build_dance_plan,
    build_sequence_plan,
)


class FakeClock:
    def __init__(self, start: float = 100.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class FakeNode:
    def __init__(self) -> None:
        self.outputs: list[tuple[str, list[object]]] = []

    def send_output(self, output_id, value, metadata=None) -> None:
        payload = value.to_pylist() if hasattr(value, 'to_pylist') else value
        self.outputs.append((output_id, payload))


def weighted_linear_balance(steps) -> float:
    turning_steps = [
        step.payload[0]
        for step in steps
        if step.output_id == 'move_tracks_sequence' and step.payload
    ]
    return sum(float(step.get('linear', 0)) * float(step.get('duration', 0.0)) for step in turning_steps)


def max_abs_track_components(steps) -> tuple[float, float]:
    track_steps = [
        step.payload[0]
        for step in steps
        if step.output_id == 'move_tracks_sequence' and step.payload
    ]
    max_linear = max((abs(float(step.get('linear', 0))) for step in track_steps), default=0.0)
    max_angular = max((abs(float(step.get('angular', 0))) for step in track_steps), default=0.0)
    return max_linear, max_angular


def test_amplify_left_dance_arm_position_clamps_to_calibrated_range() -> None:
    assert amplify_left_dance_arm_position(0) == ARM_LEFT_NEUTRAL
    assert amplify_left_dance_arm_position(ARM_LEFT_NEUTRAL) == ARM_LEFT_NEUTRAL
    assert amplify_left_dance_arm_position(300) == 300
    assert amplify_left_dance_arm_position(ARM_LEFT_UP) == ARM_LEFT_UP
    assert amplify_left_dance_arm_position(600) == ARM_LEFT_UP


def test_all_sequence_plans_start_with_audio_stop() -> None:
    for seq_id in [
        'hands-up',
        'candy',
        'party',
        'neutral',
        'wave-hello',
        'curious-scan',
        'peekaboo',
        'spin-wiggle',
        'double-take',
        'shimmy',
        'pirouette',
        'suche',
        'idle-listen',
        'idle-peek',
        'idle-fidget',
    ]:
        steps = build_sequence_plan(seq_id)
        assert steps is not None
        assert steps[0].output_id == 'stop_sequence'
        assert steps[0].at == 0.0
        assert any(step.output_id == 'move_tracks_sequence' for step in steps)


def test_action_plans_end_with_audio_stop_and_stay_under_ten_seconds() -> None:
    for seq_id in [
        'hands-up',
        'candy',
        'party',
        'neutral',
        'wave-hello',
        'curious-scan',
        'peekaboo',
        'spin-wiggle',
        'double-take',
        'shimmy',
        'pirouette',
        'suche',
    ]:
        steps = build_sequence_plan(seq_id)
        assert steps is not None
        assert steps[-1].output_id == 'stop_sequence'
        assert steps[-1].at <= 10.0


def test_turning_sequences_emit_track_motion() -> None:
    for seq_id in ['spin-wiggle', 'double-take', 'shimmy', 'pirouette', 'suche']:
        steps = build_sequence_plan(seq_id)
        assert steps is not None
        assert any(
            step.output_id == 'move_tracks_sequence' and step.payload[0]['angular'] != 0
            for step in steps
        )
        assert any(
            step.output_id == 'move_tracks_sequence' and step.payload[0]['angular'] == 0
            for step in steps
        )


def test_pirouette_is_a_full_spin_plan() -> None:
    steps = build_sequence_plan('pirouette')
    assert steps is not None

    turning_steps = [
        step for step in steps
        if step.output_id == 'move_tracks_sequence' and step.payload[0]['angular'] != 0
    ]
    assert len(turning_steps) >= 4
    assert sum(step.payload[0]['duration'] for step in turning_steps) >= 4.5


def test_double_take_includes_backdrive() -> None:
    steps = build_sequence_plan('double-take')
    assert steps is not None

    assert any(
        step.output_id == 'move_tracks_sequence' and step.payload[0]['linear'] < 0
        for step in steps
    )


def test_scheduler_emits_sequence_state_on_start_and_completion() -> None:
    clock = FakeClock()
    node = FakeNode()
    scheduler = SequenceScheduler(clock=clock)

    assert scheduler.request_sequence(node, 'idle-listen') is True
    assert any(
        output_id == 'sequence_state' and payload == [{'id': 'idle-listen', 'active': True}]
        for output_id, payload in node.outputs
    )

    clock.now += 5.0
    scheduler.emit_due_steps(node)

    assert any(
        output_id == 'sequence_state' and payload == [{'id': 'idle-listen', 'active': False}]
        for output_id, payload in node.outputs
    )


def test_new_trigger_replaces_future_steps_from_previous_sequence() -> None:
    clock = FakeClock()
    node = FakeNode()
    scheduler = SequenceScheduler(clock=clock)

    assert scheduler.request_sequence(node, 'party') is True
    clock.now += 0.5
    scheduler.emit_due_steps(node)
    assert scheduler.active_sequence_id == 'party'

    node.outputs.clear()
    assert scheduler.request_sequence(node, 'neutral') is True
    assert scheduler.active_sequence_id == 'neutral'

    clock.now += 0.5
    scheduler.emit_due_steps(node)

    assert any(output_id == 'stop_sequence' for output_id, _ in node.outputs)
    assert any(payload == [{'id': 4, 'position': HEAD_RIGHT_NEUTRAL}] for _, payload in node.outputs)
    assert all(payload != [{'id': 4, 'position': HEAD_RIGHT_UP}] for _, payload in node.outputs)


def test_unknown_sequence_is_rejected() -> None:
    scheduler = SequenceScheduler(clock=FakeClock())
    node = FakeNode()

    assert scheduler.request_sequence(node, 'not-a-scene') is False
    assert scheduler.active_sequence_id is None
    assert node.outputs == []


def test_cancel_active_sequence_emits_inactive_state() -> None:
    scheduler = SequenceScheduler(clock=FakeClock())
    node = FakeNode()

    assert scheduler.request_sequence(node, 'party') is True
    node.outputs.clear()

    assert scheduler.cancel_active(node, reason='emergency-stop') is True
    assert scheduler.active_sequence_id is None
    assert node.outputs == [
        ('stop_sequence', []),
        ('move_tracks_sequence', [{'linear': 0, 'angular': 0, 'duration': 0.0}]),
        ('sequence_state', [{'id': 'party', 'active': False}]),
    ]


def test_build_dance_plan_uses_local_track_metadata() -> None:
    plan = build_dance_plan({
        'id': '22-define-dancing-from-wall-e-score',
        'filename': '22-define-dancing-from-wall-e-score.mp3',
        'duration_ms': 143412,
        'style': 'define-dancing',
        'bpm': 108,
        'gif': 'lets-dance.gif',
    })

    assert plan is not None
    seq_id, steps = plan
    assert seq_id == 'dance:22-define-dancing-from-wall-e-score'
    assert steps[0].output_id == 'stop_sequence'
    assert any(
        step.output_id == 'play_sound_sequence'
        and step.payload == ['22-define-dancing-from-wall-e-score.mp3']
        for step in steps
    )
    assert any(step.output_id == 'move_tracks_sequence' for step in steps)


def test_scheduler_can_start_dance_mode() -> None:
    clock = FakeClock()
    node = FakeNode()
    scheduler = SequenceScheduler(clock=clock)

    assert scheduler.request_dance(node, {
        'id': '22-define-dancing-from-wall-e-score',
        'filename': '22-define-dancing-from-wall-e-score.mp3',
        'duration_ms': 143412,
        'style': 'define-dancing',
        'bpm': 108,
        'gif': 'lets-dance.gif',
    }) is True
    assert scheduler.active_sequence_id == 'dance:22-define-dancing-from-wall-e-score'
    assert any(
        output_id == 'sequence_state' and payload == [{'id': 'dance:22-define-dancing-from-wall-e-score', 'active': True}]
        for output_id, payload in node.outputs
    )


def test_build_dance_plan_supports_imperial_march_profile() -> None:
    plan = build_dance_plan({
        'id': 'imperial-march',
        'filename': 'imperial-march.mp3',
        'duration_ms': 42000,
        'style': 'imperial-march',
        'bpm': 104,
        'gif': 'danger.gif',
    })

    assert plan is not None
    seq_id, steps = plan
    assert seq_id == 'dance:imperial-march'
    assert any(
        step.output_id == 'play_gif_sequence' and step.payload == ['danger.gif']
        for step in steps
    )
    assert any(
        step.output_id == 'play_sound_sequence' and step.payload == ['imperial-march.mp3']
        for step in steps
    )
    assert any(
        step.output_id == 'move_tracks_sequence' and step.payload[0]['angular'] != 0
        for step in steps
    )


def test_style_specific_dance_plans_keep_translation_balanced() -> None:
    payloads = [
        {
            'id': '22-define-dancing-from-wall-e-score',
            'filename': '22-define-dancing-from-wall-e-score.mp3',
            'duration_ms': 143412,
            'style': 'define-dancing',
            'bpm': 108,
            'gif': 'lets-dance.gif',
        },
        {
            'id': 'imperial-march',
            'filename': 'imperial-march.mp3',
            'duration_ms': 42000,
            'style': 'imperial-march',
            'bpm': 104,
            'gif': 'danger.gif',
        },
        {
            'id': '30-stayin-alive-show-cut',
            'filename': '30-stayin-alive-show-cut.mp3',
            'duration_ms': 39000,
            'style': 'disco',
            'bpm': 104,
            'gif': 'lets-dance.gif',
        },
        {
            'id': '31-ymca-show-cut',
            'filename': '31-ymca-show-cut.mp3',
            'duration_ms': 38000,
            'style': 'showtime',
            'bpm': 126,
            'gif': 'lets-go.gif',
        },
        {
            'id': '32-ghostbusters-show-cut',
            'filename': '32-ghostbusters-show-cut.mp3',
            'duration_ms': 39000,
            'style': 'spooky-funk',
            'bpm': 116,
            'gif': 'danger.gif',
        },
        {
            'id': '33-u-can-t-touch-this-show-cut',
            'filename': '33-u-can-t-touch-this-show-cut.mp3',
            'duration_ms': 37000,
            'style': 'robotic-funk',
            'bpm': 134,
            'gif': 'lets-go.gif',
        },
    ]

    for payload in payloads:
        plan = build_dance_plan(payload)
        assert plan is not None
        _, steps = plan
        assert abs(weighted_linear_balance(steps)) <= 18.0
        assert any(step.output_id == 'play_gif_sequence' for step in steps)
        assert any(
            step.output_id == 'move_tracks_sequence' and step.payload[0]['angular'] != 0
            for step in steps
        )


def test_imperial_and_spooky_tracks_use_wider_radius_moves() -> None:
    payloads = [
        {
            'id': 'imperial-march',
            'filename': 'imperial-march.mp3',
            'duration_ms': 42000,
            'style': 'imperial-march',
            'bpm': 104,
            'gif': 'danger.gif',
        },
        {
            'id': '32-ghostbusters-show-cut',
            'filename': '32-ghostbusters-show-cut.mp3',
            'duration_ms': 39000,
            'style': 'spooky-funk',
            'bpm': 116,
            'gif': 'danger.gif',
        },
    ]

    for payload in payloads:
        plan = build_dance_plan(payload)
        assert plan is not None
        _, steps = plan
        max_linear, max_angular = max_abs_track_components(steps)
        assert max_linear >= 21.0
        assert max_angular >= 29.0
