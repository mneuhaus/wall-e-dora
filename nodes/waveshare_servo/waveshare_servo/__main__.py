"""
Main entry point for the Waveshare Servo Node.
"""

import sys
import os

# This is needed for Dora to properly find modules
package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

# Only import after setting up sys.path
from waveshare_servo.main import main

# Make this file directly runnable by Dora
if __name__ == "__main__":
    main()