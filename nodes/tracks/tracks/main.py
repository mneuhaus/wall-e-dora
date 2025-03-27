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
# Reverting to match the OLD working script's logic for THIS specific firmware.
# NO inversion, NO deadzone.
INVERT_Y_AXIS = False # Old script did not invert Y
INVERT_X_AXIS = False # Old script did not invert X
JOYSTICK_DEADZONE = 0.0 # Old script had no deadzone, set to 0.0
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

                    # Convert joystick inputs to linear and angular velocities.
                    # Directly map Y to linear, X to angular (matching old script)
                    linear = int(current_y * y_multiplier * COMMAND_SCALE)
                    angular = int(current_x * x_multiplier * COMMAND_SCALE)

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