from dora import Node
import pyarrow as pa
import serial
import time


def main():
    node = Node()
    # Initialize serial connection to the servo driver board
    ser = serial.Serial("/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FD016638-if00", 115200, timeout=1)
    # Available servo nodes definition (example)
    available_servos = {"servo1": "Servo A", "servo2": "Servo B", "servo3": "Servo C"}
    last_available_time = time.time()

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "TICK":
                print(f"""Node received:
                id: {event["id"]},
                value: {event["value"]},
                metadata: {event["metadata"]}""")
                # Check if 3 seconds have passed to output available nodes.
                current_time = time.time()
                if current_time - last_available_time >= 3:
                    node.send_output(output_id="available_nodes", data=pa.array(list(available_servos.keys())), metadata={})
                    last_available_time = current_time

            elif event["id"] == "set_servo":
                # Set servo command handler. Expects event["value"] to be [servo_id, position, speed]
                cmd = event["value"].to_py()
                servo_id, position, speed = cmd[0], cmd[1], cmd[2]
                command_str = f"{servo_id},{position},{speed}\n"
                ser.write(command_str.encode())
                print(f"Sent command to servo {servo_id}: position {position} at speed {speed}")

            elif event["id"] == "my_input_id":
                # Warning: Make sure to add my_output_id and my_input_id within the dataflow.
                node.send_output(output_id="my_output_id", data=pa.array([1, 2, 3]), metadata={})


if __name__ == "__main__":
    main()
