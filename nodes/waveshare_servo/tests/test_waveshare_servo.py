"""Focused tests for the current Waveshare servo node modules."""

import json
from unittest.mock import MagicMock

from waveshare_servo.config.handler import ConfigHandler
from waveshare_servo.outputs.servo_diagnostics import broadcast_servo_diagnostics
from waveshare_servo.outputs.servo_status import broadcast_servo_status
from waveshare_servo.outputs.servos_list import broadcast_servos_list
from waveshare_servo.servo.models import ServoModel, ServoSettings


def test_servo_model_lookup_recognizes_sc_series() -> None:
    """Known SC-series model numbers should map to friendly metadata."""
    model = ServoModel.from_model_number(15)

    assert model.name == "SC15"
    assert model.series == "SC"
    assert model.max_position == 1023


def test_servo_settings_transport_dict_normalizes_gamepad_config() -> None:
    """Transport payloads should keep a stable nested gamepad_config shape."""
    settings = ServoSettings(id=3, gamepad_config={"mode": "toggle", "invert": True})

    payload = settings.to_transport_dict()

    assert payload["id"] == 3
    assert payload["gamepad_config"] == {
        "control": "",
        "type": "",
        "mode": "toggle",
        "invert": True,
        "multiplier": 1.0,
        "isAnalog": False,
    }


def test_config_handler_get_all_servo_ids_and_delete() -> None:
    """Config helpers should return sorted IDs and delete persisted entries."""
    handler = ConfigHandler.__new__(ConfigHandler)
    handler.cached_settings = {"9": {}, "2": {}, "invalid": {}}
    handler._save_settings = MagicMock()

    assert handler.get_all_servo_ids() == [2, 9]

    handler.delete_servo_settings(2)

    assert "2" not in handler.cached_settings
    handler._save_settings.assert_called_once()


def test_config_handler_prefers_repo_root_config_when_legacy_file_exists(tmp_path) -> None:
    """The canonical repo-root config should win when both paths exist."""
    handler = ConfigHandler.__new__(ConfigHandler)
    handler.node = MagicMock()
    handler.cached_settings = {}
    handler.config_file_path = tmp_path / "config" / "servo.json"
    handler.legacy_config_file_path = tmp_path / "nodes" / "config" / "servo.json"

    handler.config_file_path.parent.mkdir(parents=True, exist_ok=True)
    handler.legacy_config_file_path.parent.mkdir(parents=True, exist_ok=True)
    handler.config_file_path.write_text(json.dumps({"5": {"id": 5, "alias": "Door"}}), encoding="utf-8")
    handler.legacy_config_file_path.write_text(json.dumps({"5": {"id": 5, "alias": ""}}), encoding="utf-8")

    handler._load_settings()

    assert handler.cached_settings["5"]["alias"] == "Door"


def test_config_handler_migrates_legacy_config_when_repo_root_is_missing(tmp_path) -> None:
    """Legacy settings should be copied into the repo-root location once."""
    handler = ConfigHandler.__new__(ConfigHandler)
    handler.node = MagicMock()
    handler.cached_settings = {}
    handler.config_file_path = tmp_path / "config" / "servo.json"
    handler.legacy_config_file_path = tmp_path / "nodes" / "config" / "servo.json"

    handler.legacy_config_file_path.parent.mkdir(parents=True, exist_ok=True)
    handler.legacy_config_file_path.write_text(json.dumps({"5": {"id": 5, "alias": "Door"}}), encoding="utf-8")

    handler._load_settings()

    assert handler.cached_settings["5"]["alias"] == "Door"
    assert json.loads(handler.config_file_path.read_text(encoding="utf-8"))["5"]["alias"] == "Door"


def test_broadcast_servo_status_uses_structured_arrow_payload() -> None:
    """Single-servo status updates should be sent as object arrays, not JSON strings."""
    node = MagicMock()
    servo = MagicMock()
    servo.settings = ServoSettings(id=4, alias="Head", model_name="SC09")

    broadcast_servo_status(node, 4, {4: servo})

    output_id, payload = node.send_output.call_args.args
    assert output_id == "servo_status"
    assert payload.to_pylist()[0]["id"] == 4
    assert payload.to_pylist()[0]["model_name"] == "SC09"


def test_broadcast_servos_list_filters_unresponsive_servos() -> None:
    """Only responsive servos should be included in the list broadcast."""
    node = MagicMock()

    responsive = MagicMock()
    responsive.is_responsive.return_value = True
    responsive.settings = ServoSettings(id=1, alias="Alpha")

    silent = MagicMock()
    silent.is_responsive.return_value = False
    silent.settings = ServoSettings(id=2, alias="Beta")

    broadcast_servos_list(node, {1: responsive, 2: silent})

    output_id, payload = node.send_output.call_args.args
    assert output_id == "servos_list"
    assert payload.to_pylist() == [responsive.settings.to_transport_dict()]


def test_broadcast_servo_diagnostics_accepts_bulk_payloads() -> None:
    """Diagnostics broadcasts should support one-to-many comparison payloads."""
    node = MagicMock()

    broadcast_servo_diagnostics(
        node,
        [
            {"id": 1, "alias": "Left", "model": {"name": "SC09"}},
            {"id": 2, "alias": "Right", "model": {"name": "SC15"}},
        ],
    )

    output_id, payload = node.send_output.call_args.args
    assert output_id == "servo_diagnostics"
    assert [entry["id"] for entry in payload.to_pylist()] == [1, 2]
