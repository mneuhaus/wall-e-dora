from dora import Node
import pyarrow as pa
from serial import Serial
import time
import os
import threading
import queue
import sys

serial_buffer = queue.Queue()

def background_serial_reader():
    try:
        ser = Serial('/dev/serial/by-id/usb-Raspberry_Pi_Pico_E6612483CB1A9621-if00', 115200, timeout=0)
        while True:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='replace')
                serial_buffer.put(line)
            time.sleep(0.1)
    except Exception as e:
        print(f"Error reading serial port in background thread: {e}")

def flush_serial_buffer():
    while not serial_buffer.empty():
        line = serial_buffer.get()
        print(line, end='')

def move_tracks():
    "Move left and right tracks at 10% speed for 5 seconds"
    print("Setting left track to 10% speed")
    print("Setting right track to 10% speed")
    time.sleep(5)
    print("Stopping left track")
    print("Stopping right track")

bg_thread = None

def start_background_thread():
    global bg_thread
    if bg_thread is None or not bg_thread.is_alive():
        bg_thread = threading.Thread(target=background_serial_reader, daemon=True)
        bg_thread.start()

def main():
    try:
        ser = Serial('/dev/serial/by-id/usb-Raspberry_Pi_E6612483CB1A9621-if00', 115200, timeout=0)
    except Exception as e:
        print("Error opening serial port for writing:", e)
        return

    start_background_thread()

    node = Node()
    
    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "tick":
                flush_serial_buffer()
            elif event["id"] == "command":
                cmd = event.get("command", "")
                if cmd:
                    ser.write((cmd + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
