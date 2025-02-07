from dora import Node
import pyarrow as pa
from serial import Serial
import time
import os

def direct_serial_logs():
    try:
        ser = Serial('/dev/serial/by-id/usb-Raspberry_Pi_Pico_E6612483CB1A9621-if00', 115200, timeout=0.1)
        while True:
            line = ser.readline().decode('utf-8', errors='replace')
            if not line:
                break
            print(line, end='')
        ser.close()
    except Exception as e:
        print(f"Error reading serial port: {e}")

def main():
    # Directly output serial logs from firmware
    direct_serial_logs()
    node = Node()
    print('woot')

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "tick":
                print(
                    f"""Node received:
                    id: {event["id"]},
                    value: {event["value"]},
                    metadata: {event["metadata"]}"""
                )


if __name__ == "__main__":
    main()
