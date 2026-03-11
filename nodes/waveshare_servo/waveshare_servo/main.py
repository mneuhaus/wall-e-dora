"""Main entrypoint for the Waveshare Servo node."""

from __future__ import annotations

import traceback

from dora import Node

from waveshare_servo.config.handler import ConfigHandler
from waveshare_servo.inputs import (
    handle_calibrate_servo,
    handle_clone_servo,
    handle_detach_servo,
    handle_factory_reset_servo,
    handle_move_servo,
    handle_read_diagnostics,
    handle_tick,
    handle_update_servo_setting,
    handle_wiggle_servo,
    scan_for_servos,
)
from waveshare_servo.servo.scanner import ServoScanner



def process_event(event, node, scanner, config, servos, next_available_id):
    """Process a single Dora event and return the updated next available ID."""
    try:
        if event["type"] != "INPUT":
            return next_available_id

        context = {
            "node": node,
            "scanner": scanner,
            "config": config,
            "servos": servos,
            "next_available_id": next_available_id,
        }

        handlers = {
            "move_servo": lambda evt: handle_move_servo(context, evt),
            "move_servo_ai": lambda evt: handle_move_servo(context, evt),
            "move_servo_sequence": lambda evt: handle_move_servo(context, evt),
            "wiggle_servo": lambda evt: handle_wiggle_servo(context, evt),
            "calibrate_servo": lambda evt: handle_calibrate_servo(context, evt),
            "update_servo_setting": lambda evt: handle_update_servo_setting(context, evt),
            "detach_servo": lambda evt: handle_detach_servo(context, evt),
            "read_servo_diagnostics": lambda evt: handle_read_diagnostics(context, evt),
            "clone_servo": lambda evt: handle_clone_servo(context, evt),
            "factory_reset_servo": lambda evt: handle_factory_reset_servo(context, evt),
            "tick": lambda evt: handle_tick(context, evt),
        }

        event_id = event["id"]
        if event_id in handlers:
            handlers[event_id](event)
        elif event_id.startswith("GAMEPAD_"):
            gamepad_event = event.copy()
            gamepad_event["id"] = event_id.replace("GAMEPAD_", "")
            from waveshare_servo.inputs.gamepad_event import handle_gamepad_event

            handle_gamepad_event(gamepad_event, context)

        return context["next_available_id"]
    except Exception as exc:
        print(f"Error processing event {event.get('id', 'unknown')}: {exc}")
        traceback.print_exc()
        return next_available_id



def main() -> None:
    """Entry point for the node."""
    try:
        node = Node()
        print("Waveshare Servo Node starting...")

        scanner = ServoScanner()
        config = ConfigHandler(node)
        servos = {}
        next_available_id = 2

        if scanner.connect():
            context = {
                "node": node,
                "scanner": scanner,
                "config": config,
                "servos": servos,
                "next_available_id": next_available_id,
            }
            scan_for_servos(context)
            next_available_id = context["next_available_id"]
        else:
            print("Failed to connect to servo controller - will retry on next tick")

        print("Starting main event loop...")
        for event in node:
            next_available_id = process_event(
                event,
                node,
                scanner,
                config,
                servos,
                next_available_id,
            )
    except Exception as exc:
        print(f"Error starting waveshare_servo node: {exc}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
