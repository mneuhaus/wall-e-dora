from dora import Node
import pyarrow as pa
from serial import Serial
import time
import os
import threading
import queue
import sys

serial_buffer = queue.Queue()
bg_thread = None

def background_serial_reader(ser):
    try:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='replace')
            serial_buffer.put('RP2040: ' + line)
    except Exception as e:
        print(f"Error reading serial port in background thread: {e}")

def flush_serial_buffer():
    while not serial_buffer.empty():
        line = serial_buffer.get()
        print(line, end='')

def start_background_thread(ser):
    global bg_thread
    if bg_thread is None or not bg_thread.is_alive():
        bg_thread = threading.Thread(target=background_serial_reader, args=(ser,), daemon=True)
        bg_thread.start()

def main():
    try:
        ser = Serial('/dev/serial/by-id/usb-Raspberry_Pi_Pico_E6612483CB1A9621-if00', 115200, timeout=0)
    except Exception as e:
        print("Error opening serial port for writing:", e)
        return

    start_background_thread(ser)

    node = Node()
    joystick_x = None
    joystick_y = None
    last_command_time = time.monotonic()

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "tick":
                pass
                # flush_serial_buffer()
            elif event["id"] == "heartbeat":
                now = time.monotonic()
                if now - last_command_time >= 0.1:
                    ser.write(("heartbeat\n").encode("utf-8"))
                    last_command_time = now
            elif event["id"] == "LEFT_ANALOG_STICK_X":
                joystick_x = event["value"][0].as_py()
            elif event["id"] == "LEFT_ANALOG_STICK_Y":
                joystick_y = event["value"][0].as_py()
            
            if joystick_x is not None and joystick_y is not None:
                now = time.monotonic()
                if now - last_command_time >= 0.1:
                    # Convert joystick inputs to linear and angular velocities.
                    # Assuming the joystick values are normalized in [-1, 1]:
                    print(joystick_y, joystick_x)
                    linear = -joystick_y * 100.0
                    angular = joystick_x * 100.0
                    cmd = f"move {linear} {angular}"
                    ser.write((cmd + "\n").encode("utf-8"))
                    print(cmd)
                    last_command_time = now


if __name__ == "__main__":
    main()
