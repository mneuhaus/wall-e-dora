"""
Configuration handler for the Waveshare Servo Node.
"""

import json
import traceback
from typing import Optional

import pyarrow as pa

# Import from servo module
from servo import ServoSettings


class ConfigHandler:
    """Handles interaction with the config node."""

    def __init__(self, node):
        self.node = node
        self.cached_settings = {}
        self.config_prefix = "servo"

    def get_servo_path(self, servo_id: int, property_name: Optional[str] = None) -> str:
        """Get the config path for a servo property."""
        base_path = f"{self.config_prefix}.{servo_id}"
        if property_name:
            return f"{base_path}.{property_name}"
        return base_path

    def update_setting(self, path: str, value: any):
        """Update a setting in the config node."""
        try:
            data = json.dumps({"path": path, "value": value})
            self.node.send_output(
                "update_setting", pa.array([data])
            )
        except Exception as e:
            print(f"Error sending update_setting: {e}")
            traceback.print_exc()

    def update_servo_setting(self, servo_id: int, property_name: str, value: any):
        """Update a specific servo setting."""
        path = self.get_servo_path(servo_id, property_name)
        self.update_setting(path, value)
        
        # Also update local cache
        if servo_id not in self.cached_settings:
            self.cached_settings[servo_id] = {}
        self.cached_settings[servo_id][property_name] = value

    def update_servo_settings(self, settings: ServoSettings):
        """Update all settings for a servo."""
        servo_id = settings.id
        servo_dict = settings.to_dict()
        
        # Update each property individually
        for prop, value in servo_dict.items():
            self.update_servo_setting(servo_id, prop, value)

    def get_servo_settings(self, servo_id: int) -> Optional[dict]:
        """Get settings for a specific servo from cache."""
        return self.cached_settings.get(servo_id, {})

    def handle_settings_updated(self, setting_path: str, new_value: any):
        """Handle a setting update from the config node."""
        # Check if this is a servo setting
        parts = setting_path.split(".")
        if len(parts) >= 2 and parts[0] == self.config_prefix:
            try:
                servo_id = int(parts[1])
                
                # Make sure we have a dict for this servo
                if servo_id not in self.cached_settings:
                    self.cached_settings[servo_id] = {}
                
                # Handle full servo settings update vs. single property update
                if len(parts) == 2:
                    # Full servo settings object
                    self.cached_settings[servo_id] = new_value
                elif len(parts) >= 3:
                    # Single property update
                    property_name = parts[2]
                    self.cached_settings[servo_id][property_name] = new_value
                
                return True
            except (ValueError, IndexError):
                print(f"Invalid servo setting path: {setting_path}")
        
        return False
