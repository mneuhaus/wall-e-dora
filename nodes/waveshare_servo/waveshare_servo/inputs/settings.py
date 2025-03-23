"""
Handler for settings events.
"""

import traceback
from typing import Dict, Any
import sys
import os

# Add the parent directory to the path for imports if needed
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from waveshare_servo.utils.event_processor import extract_event_data


def handle_settings(context, event: Dict[str, Any]) -> bool:
    """Handle settings event."""
    try:
        config = context["config"]
        data, error = extract_event_data(event)
        if data and isinstance(data, dict):
            for key, value in data.items():
                if key.startswith("servo."):
                    parts = key.split(".")
                    if len(parts) >= 2:
                        try:
                            servo_id = int(parts[1])
                            if len(parts) == 2:
                                # Full servo settings
                                config.cached_settings[servo_id] = value
                            elif len(parts) >= 3:
                                # Individual property
                                property_name = parts[2]
                                if servo_id not in config.cached_settings:
                                    config.cached_settings[servo_id] = {}
                                config.cached_settings[servo_id][property_name] = value
                        except (ValueError, IndexError):
                            continue
            return True
    except Exception as e:
        print(f"Error processing settings event: {e}")
    return False