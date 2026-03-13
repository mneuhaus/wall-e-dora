"""Basic tests for the power node."""

from collections import deque

import pytest

from power.main import BatteryTracker, main


def test_import_main():
    """Test that the main function can be imported and called."""
    with pytest.raises(RuntimeError):
        main()


def test_battery_tracker_uses_new_pack_defaults():
    """The tracker should use the configured 3S 2200mAh LiPo defaults."""
    tracker = BatteryTracker()

    assert tracker.capacity_ah == pytest.approx(2.2)
    assert tracker.nominal_capacity_ah == pytest.approx(2.2)
    assert tracker.max_voltage == pytest.approx(12.6)
    assert tracker.min_voltage == pytest.approx(9.9)


def test_voltage_curve_and_load_compensation_match_lipo_behavior():
    """Loaded voltage should be compensated and mapped via the LiPo curve."""
    tracker = BatteryTracker()

    assert tracker._voltage_to_rough_soc(12.6, 0.0) == pytest.approx(100.0)
    assert tracker._voltage_to_rough_soc(9.9, 0.0) == pytest.approx(0.0)
    assert tracker._voltage_to_rough_soc(11.79, 0.0) == pytest.approx(50.0)
    assert tracker._voltage_to_rough_soc(11.49, 0.0) == pytest.approx(20.0)
    assert tracker._voltage_to_rough_soc(11.4, 2.0) > tracker._voltage_to_rough_soc(11.4, 0.0)


def test_runtime_uses_capacity_and_average_current():
    """Runtime estimation should scale with current draw and the configured capacity."""
    tracker = BatteryTracker()
    tracker.startup_readings = tracker.min_readings_before_estimate
    tracker.current_history = deque([0.5] * 10, maxlen=10)

    runtime_seconds = tracker.estimate_remaining_time(12.24)
    expected_soc = tracker._voltage_to_rough_soc(12.24, 0.5)
    expected_seconds = (((expected_soc - tracker.threshold_soc) / 100.0) * tracker.capacity_ah / 0.5) * 0.85 * 3600

    assert runtime_seconds > 0
    assert runtime_seconds == pytest.approx(expected_seconds)
