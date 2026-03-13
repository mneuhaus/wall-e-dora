from sequence.runtime import (
    HEAD_RIGHT_NEUTRAL,
    HEAD_RIGHT_UP,
    SequenceScheduler,
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
