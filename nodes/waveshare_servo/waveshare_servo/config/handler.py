"""
Configuration handler for the Waveshare Servo Node.
Stores servo settings directly in /config/servo.json
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
    """Handles servo configuration storage."""

    def __init__(self, node):
        self.node = node
        self.cached_settings = {}
        self.config_file_path = os.path.join(project_root, "config", "servo.json")
        print(f"Using config file path: {self.config_file_path}")
        self._load_settings()

    def _load_settings(self):
        """Load settings from file or create new if not exists."""
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
        """Save current settings to file."""
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(self.cached_settings, f, indent=2)
            print(f"Saved settings to {self.config_file_path}")
        except Exception as e:
            print(f"Error saving settings: {e}")
            traceback.print_exc()

    def update_servo_setting(self, servo_id: int, property_name: str, value: any):
        """Update a specific servo setting."""
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
        """Update all settings for a servo."""
        servo_id = settings.id
        servo_dict = settings.to_dict()
        
        # Use string keys for JSON compatibility
        servo_id_str = str(servo_id)
        
        # Store all settings at once
        self.cached_settings[servo_id_str] = servo_dict
        
        # Save to disk
        self._save_settings()
        
        print(f"Updated all settings for servo {servo_id}")

    def get_servo_settings(self, servo_id: int) -> Optional[dict]:
        """Get settings for a specific servo."""
        return self.cached_settings.get(str(servo_id), {})

    def handle_settings_updated(self, setting_path: str, new_value: any):
        """
        Handle a setting update notification.
        This is kept for compatibility but not used with direct file storage.
        """
        # This method is now a no-op since we're handling settings directly
        return False