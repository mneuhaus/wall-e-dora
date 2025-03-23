#!/usr/bin/env python3
"""
Simple test script to verify imports are working correctly.
"""

import os
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))

# Try importing from the module
try:
    print("Testing imports...")
    from waveshare_servo.servo.models import ServoSettings
    from waveshare_servo.servo.controller import Servo
    from waveshare_servo.config_handler import ConfigHandler
    print("Successfully imported ServoSettings")
    print("Successfully imported Servo")
    print("Successfully imported ConfigHandler")
    
    # Create a sample instance to verify
    settings = ServoSettings(id=1)
    print(f"Created ServoSettings with id={settings.id}")
    
    print("All imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)