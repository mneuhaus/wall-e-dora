"""Tracks node entrypoint for joystick and sequence-driven movement."""

from typing import Any
import queue
import threading
import time

from dora import Node
from serial import Serial
import serial

# --- Configuration ---
SERIAL_PORT = '/dev/serial/by-id/usb-Raspberry_Pi_Pico_4250305031363913-if00'
BAUD_RATE = 115200
COMMAND_SCALE = 100.0  # Scale joystick (-1..1) to Pico command range (-100..100)

# --- Joystick Mapping Configuration ---
INVERT_Y_AXIS = False
INVERT_X_AXIS = False
JOYSTICK_DEADZONE = 0.0
EMERGENCY_STOP_HOLD_SECONDS = 2.2

# --- Easing Configuration ---
EASING_ENABLED = True
EASING_FACTOR = 0.3
MAX_ACCEL_RATE = 20

serial_buffer: queue.Queue[str] = queue.Queue()
serial_read_stop_event = threading.Event()


def background_serial_reader(ser: Serial, stop_event: threading.Event) -> None:
    """Continuously read log lines from the RP2040 in the background."""
    print('Serial reader thread started.')
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                try:
                    line_bytes = ser.read_until(b'\n')
                    if line_bytes:
                        line = line_bytes.decode('utf-8', errors='replace').strip()
                        if line:
                            serial_buffer.put('RP2040: ' + line)
                except UnicodeDecodeError as error:
                    serial_buffer.put(f'SERIAL DECODE ERROR: {error}')
                except Exception as error:
                    serial_buffer.put(f'SERIAL READ ERROR: {error}')
                    time.sleep(0.5)
            else:
                time.sleep(0.01)
        except OSError as error:
            serial_buffer.put(f'SERIAL OS ERROR: {error} - Port disconnected?')
            break
        except Exception as error:
            print(f'Unhandled error in serial reader: {error}')
            time.sleep(1)
    print('Serial reader thread finished.')


def flush_serial_buffer() -> None:
    """Print all messages currently queued in the serial buffer."""
    while not serial_buffer.empty():
        try:
            print(serial_buffer.get_nowait())
        except queue.Empty:
            break
        except Exception as error:
            print(f'Error getting from serial buffer: {error}')


def start_background_thread(ser: Serial, stop_event: threading.Event) -> threading.Thread:
    """Start the background serial reader thread."""
    thread = threading.Thread(target=background_serial_reader, args=(ser, stop_event), daemon=True)
    thread.start()
    return thread


def send_command(ser: Serial, command: str, last_command_sent: str) -> str:
    """Send a movement command to the RP2040 if it changed."""
    if command == last_command_sent:
        return last_command_sent

    try:
        print(f'Sending: {command}')
        ser.write((command + '\n').encode('utf-8'))
        ser.flush()
        return command
    except serial.SerialTimeoutException:
        print('WARN: Serial write timeout occurred.')
    except Exception as error:
        print(f'ERROR: Failed to write to serial port: {error}')
    return last_command_sent


def extract_axis_value(value: Any, axis_name: str) -> float:
    """Convert an incoming Arrow joystick value into a float."""
    try:
        value_py = value[0].as_py()
        return float(value_py)
    except IndexError:
        return 0.0
    except (ValueError, TypeError):
        print(f'WARN: Could not convert Gamepad {axis_name} value to float. Using 0.0.')
        return 0.0
    except Exception as error:
        print(f'ERROR: processing gamepad {axis_name} event: {error}')
        return 0.0


def extract_sequence_move(value: Any) -> tuple[int, int, float] | None:
    """Parse a sequence-provided track move command."""
    try:
        values = value.to_pylist() if hasattr(value, 'to_pylist') else value
        if not values:
            return None
        payload = values[0]
        if not isinstance(payload, dict):
            return None
        linear = int(payload.get('linear', 0))
        angular = int(payload.get('angular', 0))
        duration = max(0.0, float(payload.get('duration', 0.0)))
        return linear, angular, duration
    except Exception as error:
        print(f'WARN: could not parse move_tracks_sequence payload: {error}')
        return None


def compute_joystick_command(
    latest_joystick_x: float,
    latest_joystick_y: float,
    current_linear: int,
    current_angular: int,
) -> tuple[int, int, int, int]:
    """Compute the next movement command from joystick state."""
    current_x = latest_joystick_x if abs(latest_joystick_x) > JOYSTICK_DEADZONE else 0.0
    current_y = latest_joystick_y if abs(latest_joystick_y) > JOYSTICK_DEADZONE else 0.0

    y_multiplier = -1.0 if INVERT_Y_AXIS else 1.0
    x_multiplier = -1.0 if INVERT_X_AXIS else 1.0

    target_linear = int(current_y * y_multiplier * COMMAND_SCALE)
    target_angular = int(current_x * x_multiplier * COMMAND_SCALE)

    if EASING_ENABLED:
        linear_diff = target_linear - current_linear
        angular_diff = target_angular - current_angular

        if MAX_ACCEL_RATE > 0:
            linear_diff = max(min(linear_diff, MAX_ACCEL_RATE), -MAX_ACCEL_RATE)
            angular_diff = max(min(angular_diff, MAX_ACCEL_RATE), -MAX_ACCEL_RATE)

        current_linear += int(linear_diff * EASING_FACTOR)
        current_angular += int(angular_diff * EASING_FACTOR)
        linear = current_linear
        angular = current_angular
    else:
        linear = target_linear
        angular = target_angular
        current_linear = linear
        current_angular = angular

    return linear, angular, current_linear, current_angular


def main() -> None:
    """Initialize serial, then forward joystick and sequence commands to the RP2040."""
    ser = None
    reader_thread = None
    try:
        print(f'Attempting to open serial port {SERIAL_PORT} at {BAUD_RATE} baud...')
        ser = Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1, write_timeout=0.5)
        print('Serial port opened successfully.')
    except Exception as error:
        print(f'FATAL: Error opening serial port {SERIAL_PORT}: {error}')
        print("Check connection, permissions (e.g., 'dialout' group), and port ID.")
        return

    serial_read_stop_event.clear()
    reader_thread = start_background_thread(ser, serial_read_stop_event)

    node = Node()
    latest_joystick_x = 0.0
    latest_joystick_y = 0.0
    last_command_sent = ''

    current_linear = 0
    current_angular = 0
    target_linear = 0
    target_angular = 0

    sequence_linear = 0
    sequence_angular = 0
    sequence_override_until = 0.0
    emergency_stop_until = 0.0

    print('Waiting for Dora events...')
    try:
        for event in node:
            event_type = event['type']
            if event_type == 'INPUT':
                event_id = event['id']

                if event_id == 'tick':
                    flush_serial_buffer()
                    now = time.monotonic()

                    if now < emergency_stop_until:
                        linear = 0
                        angular = 0
                        current_linear = 0
                        current_angular = 0
                        target_linear = 0
                        target_angular = 0
                    elif now < sequence_override_until:
                        linear = sequence_linear
                        angular = sequence_angular
                        current_linear = linear
                        current_angular = angular
                    else:
                        if sequence_override_until != 0.0:
                            sequence_override_until = 0.0
                            sequence_linear = 0
                            sequence_angular = 0
                        linear, angular, current_linear, current_angular = compute_joystick_command(
                            latest_joystick_x,
                            latest_joystick_y,
                            current_linear,
                            current_angular,
                        )
                        target_linear = linear
                        target_angular = angular

                    last_command_sent = send_command(ser, f'move {linear} {angular}', last_command_sent)

                elif event_id == 'heartbeat':
                    try:
                        ser.write(b'heartbeat\n')
                        ser.flush()
                    except Exception as error:
                        print(f'ERROR: Failed to write heartbeat: {error}')

                elif event_id == 'move_tracks_sequence':
                    if time.monotonic() < emergency_stop_until:
                        print('Ignoring sequence track move during emergency-stop hold')
                        continue

                    move = extract_sequence_move(event['value'])
                    if move is None:
                        continue

                    linear, angular, duration = move
                    sequence_linear = linear
                    sequence_angular = angular
                    sequence_override_until = time.monotonic() + duration if duration > 0.0 else 0.0
                    current_linear = linear
                    current_angular = angular
                    target_linear = linear
                    target_angular = angular
                    print(f'Sequence override: move {linear} {angular} for {duration:.2f}s')
                    last_command_sent = send_command(ser, f'move {linear} {angular}', last_command_sent)

                elif event_id == 'GAMEPAD_LEFT_ANALOG_STICK_X':
                    latest_joystick_x = extract_axis_value(event['value'], 'X')

                elif event_id == 'GAMEPAD_LEFT_ANALOG_STICK_Y':
                    latest_joystick_y = extract_axis_value(event['value'], 'Y')

                elif event_id == 'emergency_stop':
                    emergency_stop_until = time.monotonic() + EMERGENCY_STOP_HOLD_SECONDS
                    sequence_override_until = 0.0
                    sequence_linear = 0
                    sequence_angular = 0
                    current_linear = 0
                    current_angular = 0
                    target_linear = 0
                    target_angular = 0
                    print(
                        f'Emergency stop engaged for {EMERGENCY_STOP_HOLD_SECONDS:.1f}s; halting tracks'
                    )
                    last_command_sent = send_command(ser, 'move 0 0', last_command_sent)

            elif event_type == 'STOP':
                print('Received STOP event. Exiting.')
                break
            elif event_type == 'ERROR':
                print(f"Received ERROR from Dora node: {event.get('error')}")

    except KeyboardInterrupt:
        print('\nKeyboard interrupt detected. Stopping...')
    finally:
        serial_read_stop_event.set()

        if ser and ser.is_open:
            try:
                current_linear = 0
                current_angular = 0
                target_linear = 0
                target_angular = 0

                print('Sending stop command (move 0 0)...')
                ser.write(b'move 0 0\n')
                ser.flush()
                time.sleep(0.1)
                ser.close()
                print('Serial port closed.')
            except Exception as error:
                print(f'Error sending stop command or closing serial port: {error}')

        if reader_thread and reader_thread.is_alive():
            print('Waiting for serial reader thread to finish...')
            reader_thread.join(timeout=1.0)
            if reader_thread.is_alive():
                print('WARN: Serial reader thread did not exit cleanly.')

        print('Application finished.')


if __name__ == '__main__':
    main()
