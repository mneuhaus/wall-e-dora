"""Configuration handler for the Waveshare Servo Node.

Handles loading, saving, and accessing servo settings stored directly
in the project's `/config/servo.json` file.

Note: This is a temporary direct file handler. It's intended to be
refactored to use the central `config` node in the future.
"""

import json
import traceback
import sys
import os
from typing import Optional, Dict, Any
from pathlib import Path

# Add the parent directory to the path for imports if needed
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
project_root = os.path.dirname(parent_dir)  # Fixed: one level up from parent_dir
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from servo module
from waveshare_servo.servo.models import ServoSettings


class ConfigHandler:
    """Handles servo configuration storage directly in a JSON file."""

    def __init__(self, node):
        """Initialize the ConfigHandler.

        Args:
            node: The Dora node instance (currently unused but kept for
                  future compatibility with the config node).
        """
        self.node = node
        self.cached_settings = {}
        self.config_file_path = os.path.join(project_root, "config", "servo.json")
        print(f"Using config file path: {self.config_file_path}")
        self._load_settings()

    def _load_settings(self):
        """Load settings from the JSON file or create an empty one."""
        try:
            config_dir = os.path.dirname(self.config_file_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r') as f:
                    self.cached_settings = json.load(f)
                print(f"Loaded settings from {self.config_file_path}")
            else:
                # Initialize with empty settings
                self.cached_settings = {}
                self._save_settings()
                print(f"Created new settings file at {self.config_file_path}")
        except Exception as e:
            print(f"Error loading settings: {e}")
            traceback.print_exc()
            self.cached_settings = {}

    def _save_settings(self):
        """Save the current cached settings to the JSON file."""
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(self.cached_settings, f, indent=2)
            print(f"Saved settings to {self.config_file_path}")
        except Exception as e:
            print(f"Error saving settings: {e}")
            traceback.print_exc()

    def update_servo_setting(self, servo_id: int, property_name: str, value: Any):
        """Update a specific setting for a given servo and save to file.

        Args:
            servo_id: The ID of the servo to update.
            property_name: The name of the setting property (e.g., 'alias', 'speed').
            value: The new value for the setting.
        """
        # Initialize servo settings if needed
        servo_id_str = str(servo_id)  # Use string keys for JSON compatibility
        if servo_id_str not in self.cached_settings:
            self.cached_settings[servo_id_str] = {}
            
        # Update the setting
        self.cached_settings[servo_id_str][property_name] = value
        
        # Save to disk
        self._save_settings()
        
        print(f"Updated setting: servo {servo_id}, {property_name} = {value}")

    def update_servo_settings(self, settings: ServoSettings):
        """Update all settings for a servo based on a ServoSettings object.

        Args:
            settings: A ServoSettings object containing the new settings.
        """
        servo_id = settings.id
        servo_dict = settings.to_dict()
        
        # Use string keys for JSON compatibility
        servo_id_str = str(servo_id)
        
        # Store all settings at once
        self.cached_settings[servo_id_str] = servo_dict
        
        # Save to disk
        self._save_settings()
        
        print(f"Updated all settings for servo {servo_id}")

    def get_servo_settings(self, servo_id: int) -> Optional[Dict[str, Any]]:
        """Get the cached settings dictionary for a specific servo.

        Args:
            servo_id: The ID of the servo whose settings are requested.

        Returns:
            A dictionary containing the servo's settings, or an empty dictionary
            if the servo ID is not found in the cache.
        """
        return self.cached_settings.get(str(servo_id), {})

    def handle_settings_updated(self, setting_path: str, new_value: Any) -> bool:
        """Handle a setting update notification (placeholder).

        This method is intended for integration with the central config node.
        In the current direct file-based implementation, it's a no-op.

        Args:
            setting_path: The dot-notation path of the updated setting.
            new_value: The new value of the setting.

        Returns:
            Always False in the current implementation.
        """
        # This method is now a no-op since we're handling settings directly
        return False
