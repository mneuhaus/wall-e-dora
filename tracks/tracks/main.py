from dora import Node
import pyarrow as pa
import serial
import time
import os


def queue_serial_logs():
    queue_file = "/tmp/tracks_serial_queue.txt"
    try:
        ser = serial.Serial('/dev/serial/by-id/usb-Raspberry_Pi_Pico_E6612483CB1A9621-if00', 115200, timeout=0.1)
        lines = []
        while True:
            line = ser.readline().decode('utf-8', errors='replace')
            if not line:
                break
            lines.append(line)
        ser.close()
        if lines:
            with open(queue_file, "a") as f:
                f.writelines(lines)
    except Exception as e:
        print(f"Error reading serial port: {e}")

def process_serial_queue():
    queue_file = "/tmp/tracks_serial_queue.txt"
    if os.path.exists(queue_file):
        with open(queue_file, "r") as f:
            queue_content = f.read()
        if queue_content:
            print("Queued Serial Logs:")
            print(queue_content)
        # Clear the queue file after processing
        open(queue_file, "w").close()

def main():
    # Queue serial logs from firmware and process any queued output
    queue_serial_logs()
    process_serial_queue()
    node = Node()

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "TICK":
                print(
                    f"""Node received:
                id: {event["id"]},
                value: {event["value"]},
                metadata: {event["metadata"]}"""
                )

            elif event["id"] == "my_input_id":
                # Warning: Make sure to add my_output_id and my_input_id within the dataflow.
                node.send_output(
                    output_id="my_output_id", data=pa.array([1, 2, 3]), metadata={}
                )


if __name__ == "__main__":
    main()
