"""
Handler for tick events.
"""

import traceback
from typing import Dict, Any, Optional


def handle_tick(manager, event: Dict[str, Any]) -> bool:
    """Handle tick event."""
    try:
        manager.scan_for_servos()
        return True
    except Exception as e:
        print(f"Error processing tick event: {e}")
        return False
