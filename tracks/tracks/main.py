from dora import Node
import pyarrow as pa
from serial import Serial
import time
import os
import threading
import queue

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

def main():
    bg_thread = threading.Thread(target=background_serial_reader, daemon=True)
    bg_thread.start()

    node = Node()
    print('woot')

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "tick":
                flush_serial_buffer()
                print(
                    f"""Node received:
                    id: {event["id"]},
                    value: {event["value"]},
                    metadata: {event["metadata"]}"""
                )


if __name__ == "__main__":
    main()
