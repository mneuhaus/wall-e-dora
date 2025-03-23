"""
Main entry point for the Waveshare Servo Node.
"""

import traceback
from dora import Node

# Import from local modules without package name
from manager import ServoManager

# Make this file directly runnable by Dora (without imports)
def main():
    """Entry point for the node."""
    try:
        node = Node()
        print("Waveshare Servo Node starting...")
        
        # Initialize servo manager
        manager = ServoManager(node)
        manager.initialize()
        
        print("Starting main event loop...")
        # Main event loop
        for event in node:
            try:
                # Process incoming events
                manager.process_event(event)
            except Exception as e:
                print(f"Unexpected error in event loop: {e}")
                traceback.print_exc()
    except Exception as e:
        print(f"Error starting waveshare_servo node: {e}")
        traceback.print_exc()
        # Don't re-raise exception so the process exits gracefully


if __name__ == "__main__":
    main()
