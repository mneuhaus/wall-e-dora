"""
Waveshare Servo Node for WALL-E-DORA project.

This node handles all servo-related operations:
- Servo discovery and ID assignment
- Servo movement and control
- Servo calibration
- Servo settings management via the config node
"""

import traceback
import sys
import os
from typing import Dict

from dora import Node

# Import local modules with direct imports
from waveshare_servo.servo.controller import Servo
from waveshare_servo.servo.scanner import ServoScanner
from waveshare_servo.config.handler import ConfigHandler
from waveshare_servo.inputs import (
    handle_move_servo, 
    handle_wiggle_servo, 
    handle_calibrate_servo,
    handle_update_servo_setting,
    handle_tick, 
    handle_settings,
    handle_setting_updated,
    scan_for_servos
)


def process_event(event, node, scanner, config, servos, next_available_id):
    """Process an incoming event."""
    try:
        if event["type"] != "INPUT":
            return next_available_id
            
        event_id = event["id"]
        
        # Build context for handlers
        context = {
            "node": node,
            "scanner": scanner, 
            "config": config,
            "servos": servos,
            "next_available_id": next_available_id
        }
        
        # Map event IDs to handler functions
        handlers = {
            "move_servo": lambda evt: handle_move_servo(context, evt),
            "wiggle_servo": lambda evt: handle_wiggle_servo(context, evt),
            "calibrate_servo": lambda evt: handle_calibrate_servo(context, evt),
            "update_servo_setting": lambda evt: handle_update_servo_setting(context, evt),
            "tick": lambda evt: handle_tick(context, evt),
            # We no longer need these handlers as we're handling settings directly
            # "settings": lambda evt: handle_settings(context, evt),
            # "setting_updated": lambda evt: handle_setting_updated(context, evt)
        }
        
        # Call the appropriate handler if available
        if event_id in handlers:
            handlers[event_id](event)
        
        # Return potentially updated next_available_id
        return context["next_available_id"]
        
    except Exception as e:
        print(f"Error processing event {event.get('id', 'unknown')}: {e}")
        traceback.print_exc()
        return next_available_id


def main():
    """Entry point for the node."""
    try:
        node = Node()
        print("Waveshare Servo Node starting...")
        
        # Initialize components
        scanner = ServoScanner()
        config = ConfigHandler(node)
        servos = {}
        next_available_id = 2  # Reserved IDs start from 2
        
        # Initial connection and scanning
        if scanner.connect():
            context = {
                "node": node,
                "scanner": scanner, 
                "config": config,
                "servos": servos,
                "next_available_id": next_available_id
            }
            scan_for_servos(context)
            next_available_id = context["next_available_id"]
        else:
            print("Failed to connect to servo controller - will retry on next tick")
        
        print("Starting main event loop...")
        # Main event loop
        for event in node:
            try:
                # Process incoming events
                next_available_id = process_event(
                    event, node, scanner, config, servos, next_available_id
                )
            except Exception as e:
                print(f"Unexpected error in event loop: {e}")
                traceback.print_exc()
    except Exception as e:
        print(f"Error starting waveshare_servo node: {e}")
        traceback.print_exc()
        # Don't re-raise exception so the process exits gracefully


if __name__ == "__main__":
    main()