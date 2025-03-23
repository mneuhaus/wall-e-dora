"""
Handler for settings events.
"""

import traceback
from typing import Dict, Any, Optional

from event_processor import extract_event_data


def handle_settings(manager, event: Dict[str, Any]) -> bool:
    """Handle settings event."""
    try:
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
                                manager.config.cached_settings[servo_id] = value
                            elif len(parts) >= 3:
                                # Individual property
                                property_name = parts[2]
                                if servo_id not in manager.config.cached_settings:
                                    manager.config.cached_settings[servo_id] = {}
                                manager.config.cached_settings[servo_id][property_name] = value
                        except (ValueError, IndexError):
                            continue
            return True
    except Exception as e:
        print(f"Error processing settings event: {e}")
    return False
