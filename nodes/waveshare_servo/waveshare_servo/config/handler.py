"""Configuration handler for the Waveshare Servo Node."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any, Optional

from waveshare_servo.servo.models import ServoSettings


class ConfigHandler:
    """Handles servo configuration storage directly in a JSON file."""

    def __init__(self, node):
        self.node = node
        self.cached_settings: dict[str, dict[str, Any]] = {}
        config_dir = Path(__file__).resolve().parent
        repo_root = config_dir.parents[3]
        self.config_file_path = repo_root / "config" / "servo.json"
        self.legacy_config_file_path = repo_root / "nodes" / "config" / "servo.json"
        print(f"Using config file path: {self.config_file_path}")
        if self.legacy_config_file_path.exists():
            print(f"Legacy config fallback available at: {self.legacy_config_file_path}")
        self._load_settings()

    def _read_settings_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Load a JSON settings file from disk."""
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError(f"Expected a JSON object in {path}")

        return data

    def _load_settings(self) -> None:
        """Load settings from disk, preferring the repo-root config path."""
        try:
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)

            if self.config_file_path.exists():
                self.cached_settings = self._read_settings_file(self.config_file_path)
                print(f"Loaded settings from {self.config_file_path}")
                if self.legacy_config_file_path.exists():
                    print(
                        "Ignoring legacy settings file at "
                        f"{self.legacy_config_file_path}; using repo-root config instead"
                    )
            elif self.legacy_config_file_path.exists():
                self.cached_settings = self._read_settings_file(self.legacy_config_file_path)
                self._save_settings()
                print(
                    "Migrated legacy settings from "
                    f"{self.legacy_config_file_path} to {self.config_file_path}"
                )
            else:
                self.cached_settings = {}
                self._save_settings()
                print(f"Created new settings file at {self.config_file_path}")
        except Exception as exc:
            print(f"Error loading settings: {exc}")
            traceback.print_exc()
            self.cached_settings = {}

    def _save_settings(self) -> None:
        """Persist the current settings cache to disk."""
        try:
            with self.config_file_path.open("w", encoding="utf-8") as handle:
                json.dump(self.cached_settings, handle, indent=2)
            print(f"Saved settings to {self.config_file_path}")
        except Exception as exc:
            print(f"Error saving settings: {exc}")
            traceback.print_exc()

    def get_all_servo_ids(self) -> list[int]:
        """Return all persisted servo IDs as integers."""
        servo_ids: list[int] = []
        for servo_id in self.cached_settings.keys():
            try:
                servo_ids.append(int(servo_id))
            except (TypeError, ValueError):
                continue
        return sorted(servo_ids)

    def update_servo_setting(self, servo_id: int, property_name: str, value: Any) -> None:
        """Update a specific setting for a given servo and save to disk."""
        servo_id_str = str(servo_id)
        self.cached_settings.setdefault(servo_id_str, {})
        self.cached_settings[servo_id_str][property_name] = value
        self._save_settings()
        print(f"Updated setting: servo {servo_id}, {property_name} = {value}")

    def update_servo_settings(self, settings: ServoSettings) -> None:
        """Replace the stored settings for a servo using a dataclass instance."""
        self.cached_settings[str(settings.id)] = settings.to_dict()
        self._save_settings()
        print(f"Updated all settings for servo {settings.id}")

    def get_servo_settings(self, servo_id: int) -> Optional[dict[str, Any]]:
        """Get the cached settings dictionary for a specific servo."""
        return self.cached_settings.get(str(servo_id), {})

    def delete_servo_settings(self, servo_id: int) -> None:
        """Delete all persisted settings for a servo if present."""
        if str(servo_id) in self.cached_settings:
            del self.cached_settings[str(servo_id)]
            self._save_settings()
            print(f"Deleted settings for servo {servo_id}")

    def handle_settings_updated(self, setting_path: str, new_value: Any) -> bool:
        """Placeholder for future config-node integration."""
        return False
