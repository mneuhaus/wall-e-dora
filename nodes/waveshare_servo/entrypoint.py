#!/usr/bin/env python3
"""Entry point script for the Waveshare Servo Node.

This script ensures the package directory is in the Python path and then
calls the main function from the `waveshare_servo.main` module. This allows
Dora to execute the node using this file as the target path.
"""

import sys
import os

# Add the package directory to the path
package_dir = os.path.dirname(os.path.abspath(__file__))
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

# Import the main function
from waveshare_servo.main import main

# Run the node
if __name__ == "__main__":
    main()
