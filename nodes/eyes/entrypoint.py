"""Entry point for the eyes node."""
import sys
import os

# Add the current directory to the path so we can import the eyes package
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from eyes.main import main

if __name__ == "__main__":
    main()