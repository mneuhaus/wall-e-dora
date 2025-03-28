from dora import Node
import pyarrow as pa
from serial import Serial
import time
import os
import threading
import queue
import sys
import math # Import math for abs
import serial # Explicitly import serial exceptions if needed

# --- Configuration ---
SERIAL_PORT = '/dev/serial/by-id/usb-Raspberry_Pi_Pico_E6612483CB1A9621-if00'
BAUD_RATE = 115200
COMMAND_SCALE = 100.0 # Scale joystick (-1..1) to Pico command range (-100..100)

# --- Joystick Mapping Configuration ---
# Configuration for joystick axis mapping
INVERT_Y_AXIS = False # Keep forward/backward as is
INVERT_X_AXIS = True  # Invert left/right to fix the turning direction
JOYSTICK_DEADZONE = 0.0 # Old script had no deadzone, set to 0.0

# --- Easing Configuration ---
EASING_ENABLED = True # Enable/disable easing
EASING_FACTOR = 0.3  # Easing factor (0.0-1.0): lower = smoother but less responsive
MAX_ACCEL_RATE = 20   # Maximum acceleration change per tick (prevents abrupt changes)
# ---

serial_buffer = queue.Queue()
serial_read_stop_event = threading.Event() # To signal the reader thread to stop

# --- Background Serial Reader (Corrected read_until) ---
def background_serial_reader(ser, stop_event):
    """Continuously reads lines from serial and puts them in a queue."""
    print("Serial reader thread started.")
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                try:
                    # Use read_until, default timeout is from Serial object
                    line_bytes = ser.read_until(b'\n')
                    if line_bytes:
                         line = line_bytes.decode('utf-8', errors='replace').strip()
                         if line:
                              serial_buffer.put('RP2040: ' + line)
                except UnicodeDecodeError as ude:
                    serial_buffer.put(f"SERIAL DECODE ERROR: {ude}")
                except Exception as read_err:
                    serial_buffer.put(f"SERIAL READ ERROR: {read_err}")
                    time.sleep(0.5)
            else:
                # Prevent busy-waiting when no data
                time.sleep(0.01)
        except OSError as e:
            serial_buffer.put(f"SERIAL OS ERROR: {e} - Port disconnected?")
            break # Exit thread if port has a major issue
        except Exception as e:
            print(f"Unhandled error in serial reader: {e}")
            time.sleep(1)
    print("Serial reader thread finished.")


def flush_serial_buffer():
    """Prints all messages currently in the serial buffer."""
    while not serial_buffer.empty():
        try:
            line = serial_buffer.get_nowait()
            print(line)
        except queue.Empty:
            break
        except Exception as e:
            print(f"Error getting from serial buffer: {e}")

def start_background_thread(ser, stop_event):
    """Starts the background serial reader thread."""
    thread = threading.Thread(target=background_serial_reader, args=(ser, stop_event), daemon=True)
    thread.start()
    return thread

# --- Main Application ---
def main():
    ser = None
    reader_thread = None
    try:
        print(f"Attempting to open serial port {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1, write_timeout=0.5)
        print("Serial port opened successfully.")
    except Exception as e:
        print(f"FATAL: Error opening serial port {SERIAL_PORT}: {e}")
        print("Check connection, permissions (e.g., 'dialout' group), and port ID.")
        return

    serial_read_stop_event.clear()
    reader_thread = start_background_thread(ser, serial_read_stop_event)

    node = Node()
    latest_joystick_x = 0.0
    latest_joystick_y = 0.0
    last_command_sent = ""
    
    # Variables for easing implementation
    current_linear = 0
    current_angular = 0
    target_linear = 0
    target_angular = 0

    print("Waiting for Dora events...")
    try:
        for event in node:
            if event["type"] == "INPUT":
                event_id = event["id"]

                if event_id == "tick":
                    flush_serial_buffer() # Print Pico messages

                    # --- Apply Mapping (No Deadzone, No Inversion - matching old script) ---
                    current_x_raw = latest_joystick_x
                    current_y_raw = latest_joystick_y

                    # Apply deadzone (effectively disabled if JOYSTICK_DEADZONE is 0.0)
                    current_x = current_x_raw if abs(current_x_raw) > JOYSTICK_DEADZONE else 0.0
                    current_y = current_y_raw if abs(current_y_raw) > JOYSTICK_DEADZONE else 0.0

                    # Apply axis inversion (effectively disabled if flags are False)
                    y_multiplier = -1.0 if INVERT_Y_AXIS else 1.0
                    x_multiplier = -1.0 if INVERT_X_AXIS else 1.0

                    # Calculate target velocities from joystick input
                    target_linear = int(current_y * y_multiplier * COMMAND_SCALE)
                    target_angular = int(current_x * x_multiplier * COMMAND_SCALE)
                    
                    if EASING_ENABLED:
                        # Apply easing to smooth movement
                        # Calculate differences between current and target values
                        linear_diff = target_linear - current_linear
                        angular_diff = target_angular - current_angular
                        
                        # Limit maximum change rate if needed
                        if MAX_ACCEL_RATE > 0:
                            linear_diff = max(min(linear_diff, MAX_ACCEL_RATE), -MAX_ACCEL_RATE)
                            angular_diff = max(min(angular_diff, MAX_ACCEL_RATE), -MAX_ACCEL_RATE)
                        
                        # Apply easing using the easing factor
                        current_linear += int(linear_diff * EASING_FACTOR)
                        current_angular += int(angular_diff * EASING_FACTOR)
                        
                        # Set linear and angular to the eased values
                        linear = current_linear
                        angular = current_angular
                    else:
                        # No easing - direct mapping
                        linear = target_linear
                        angular = target_angular
                        current_linear = linear
                        current_angular = angular

                    cmd = f"move {linear} {angular}"

                    if cmd != last_command_sent:
                        try:
                            # Simplified log to match old script's effective output
                            print(f"Sending: {cmd}")
                            ser.write((cmd + "\n").encode("utf-8"))
                            ser.flush()
                            last_command_sent = cmd
                        except serial.SerialTimeoutException:
                            print("WARN: Serial write timeout occurred.")
                        except Exception as write_err:
                            print(f"ERROR: Failed to write to serial port: {write_err}")

                elif event_id == "heartbeat":
                     try:
                         # print("Sending: heartbeat") # Reduce noise
                         ser.write(("heartbeat\n").encode("utf-8"))
                         ser.flush()
                     except Exception as write_err:
                          print(f"ERROR: Failed to write heartbeat: {write_err}")

                # Robust handling of incoming joystick values
                elif event_id == "GAMEPAD_LEFT_ANALOG_STICK_X":
                    try:
                        value_py = event["value"][0].as_py()
                        try:
                             latest_joystick_x = float(value_py)
                        except (ValueError, TypeError):
                             print(f"WARN: Could not convert Gamepad X value '{value_py}' (type: {type(value_py)}) to float. Using 0.0.")
                             latest_joystick_x = 0.0
                    except IndexError:
                         latest_joystick_x = 0.0
                    except Exception as e:
                         print(f"ERROR: processing gamepad X event: {e}")
                         latest_joystick_x = 0.0

                elif event_id == "GAMEPAD_LEFT_ANALOG_STICK_Y":
                    try:
                        value_py = event["value"][0].as_py()
                        try:
                             latest_joystick_y = float(value_py)
                        except (ValueError, TypeError):
                             print(f"WARN: Could not convert Gamepad Y value '{value_py}' (type: {type(value_py)}) to float. Using 0.0.")
                             latest_joystick_y = 0.0
                    except IndexError:
                         latest_joystick_y = 0.0
                    except Exception as e:
                         print(f"ERROR: processing gamepad Y event: {e}")
                         latest_joystick_y = 0.0

            elif event["type"] == "STOP":
                print("Received STOP event. Exiting.")
                break
            elif event["type"] == "ERROR":
                 print(f"Received ERROR from Dora node: {event.get('error')}")

    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Stopping...")
    finally:
        serial_read_stop_event.set()

        if ser and ser.is_open:
            try:
                # Reset the easing values to ensure immediate stop
                current_linear = 0
                current_angular = 0
                target_linear = 0
                target_angular = 0
                
                print("Sending stop command (move 0 0)...")
                ser.write(("move 0 0\n").encode("utf-8"))
                ser.flush()
                time.sleep(0.1)
                ser.close()
                print("Serial port closed.")
            except Exception as e:
                print(f"Error sending stop command or closing serial port: {e}")

        if reader_thread and reader_thread.is_alive():
            print("Waiting for serial reader thread to finish...")
            reader_thread.join(timeout=1.0)
            if reader_thread.is_alive():
                print("WARN: Serial reader thread did not exit cleanly.")

        print("Application finished.")

if __name__ == "__main__":
    main()