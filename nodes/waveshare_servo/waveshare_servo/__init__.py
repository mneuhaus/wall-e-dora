"""
Waveshare Servo Node for WALL-E-DORA project.
"""

import os

# Define the path to the README file relative to the package directory
readme_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")

# Read the content of the README file
try:
    with open(readme_path, "r", encoding="utf-8") as f:
        __doc__ = f.read()
except FileNotFoundError:
    __doc__ = "README file not found."

# Use local imports instead of package imports
from config_handler import ConfigHandler
from event_processor import extract_event_data
from manager import ServoManager
from models import ServoSettings
from scanner import ServoScanner
from servo import Servo

__all__ = [
    'ConfigHandler',
    'extract_event_data',
    'ServoManager',
    'ServoSettings',
    'ServoScanner',
    'Servo',
]