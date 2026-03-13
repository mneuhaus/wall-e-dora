"""Tests for simple face tracking helpers."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))

from web.main import (  # noqa: E402
    FACE_TRACKING_CENTER_POSITION,
    FACE_TRACKING_MAX_POSITION,
    FACE_TRACKING_MIN_POSITION,
    blend_face_tracking_observation,
    clamp_face_tracking_position,
    compute_face_tracking_target,
    compute_face_tracking_face_area,
    compute_next_face_tracking_step,
    select_next_face_tracking_search_target,
    project_face_tracking_center,
    select_face_tracking_face,
)


def test_compute_face_tracking_target_returns_center_in_deadzone() -> None:
    """A face near the middle should not move the head."""
    assert compute_face_tracking_target(640, 320) == FACE_TRACKING_CENTER_POSITION
    assert abs(compute_face_tracking_target(640, 340) - FACE_TRACKING_CENTER_POSITION) <= 1


def test_compute_face_tracking_target_clamps_to_edges() -> None:
    """Faces near the frame edges should map to the servo limits."""
    assert compute_face_tracking_target(640, 0) == FACE_TRACKING_MIN_POSITION
    assert compute_face_tracking_target(640, 640) == FACE_TRACKING_MAX_POSITION


def test_compute_next_face_tracking_step_moves_smoothly() -> None:
    """Head tracking should move in limited, smooth steps."""
    next_left = compute_next_face_tracking_step(FACE_TRACKING_CENTER_POSITION, FACE_TRACKING_MIN_POSITION)
    next_right = compute_next_face_tracking_step(FACE_TRACKING_CENTER_POSITION, FACE_TRACKING_MAX_POSITION)

    assert FACE_TRACKING_MIN_POSITION <= next_left < FACE_TRACKING_CENTER_POSITION
    assert FACE_TRACKING_CENTER_POSITION < next_right <= FACE_TRACKING_MAX_POSITION


def test_clamp_face_tracking_position_limits_range() -> None:
    """Servo outputs should never exceed the safe head-pivot range."""
    assert clamp_face_tracking_position(FACE_TRACKING_MIN_POSITION - 100) == FACE_TRACKING_MIN_POSITION
    assert clamp_face_tracking_position(FACE_TRACKING_MAX_POSITION + 100) == FACE_TRACKING_MAX_POSITION


def test_select_face_tracking_face_prefers_stable_candidate() -> None:
    """Face selection should stay with the closest strong candidate by default."""
    detected_faces = [
        {'center_x': 0.25, 'width': 0.16, 'height': 0.25, 'score': 0.93},
        {'center_x': 0.77, 'width': 0.12, 'height': 0.19, 'score': 0.95},
    ]

    selected_index, switched_at = select_face_tracking_face(
        detected_faces,
        reference_center_x=0.22,
        reference_area=compute_face_tracking_face_area(detected_faces[0]),
        now=3.0,
        last_face_switch_at=2.6,
    )

    assert selected_index == 0
    assert switched_at == 2.6


def test_blend_face_tracking_observation_smooths_and_projects_forward() -> None:
    """Tracking should smooth raw observations instead of snapping directly."""
    center_x, velocity_x, area = blend_face_tracking_observation(
        observed_center_x=0.62,
        observed_area=0.06,
        previous_center_x=0.50,
        previous_velocity_x=0.0,
        previous_area=0.04,
        delta_time=0.2,
    )

    assert 0.50 < center_x < 0.62
    assert velocity_x > 0.0
    assert 0.04 < area < 0.06


def test_project_face_tracking_center_clamps_prediction() -> None:
    """Short-lived motion prediction should stay inside the frame."""
    assert 0.0 <= project_face_tracking_center(0.96, 0.9, elapsed=0.3) <= 1.0


def test_select_next_face_tracking_search_target_prefers_wide_sweeps() -> None:
    """Search mode should bounce across the wider left/right range."""
    next_from_left = select_next_face_tracking_search_target(FACE_TRACKING_MIN_POSITION + 8)
    next_from_right = select_next_face_tracking_search_target(FACE_TRACKING_MAX_POSITION - 8)
    next_from_center = select_next_face_tracking_search_target(FACE_TRACKING_CENTER_POSITION)

    assert next_from_left >= FACE_TRACKING_MAX_POSITION - 18
    assert next_from_right <= FACE_TRACKING_MIN_POSITION + 18
    assert next_from_center >= FACE_TRACKING_MAX_POSITION - 18
