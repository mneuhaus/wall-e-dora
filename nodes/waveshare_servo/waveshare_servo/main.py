from dora import Node
import pyarrow as pa
from scservo_sdk import *
import time


def main():
    node = Node()
    # SCServo configuration
    DEVICENAME = '/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FD016638-if00'
    BAUDRATE = 1000000
    SCS_ID = 1
    ADDR_SCS_GOAL_ACC = 41
    ADDR_SCS_GOAL_SPEED = 46
    ADDR_SCS_GOAL_POSITION = 42
    ADDR_SCS_PRESENT_POSITION = 56
    SCS_MINIMUM_POSITION_VALUE = 100
    SCS_MAXIMUM_POSITION_VALUE = 4000
    SCS_MOVING_STATUS_THRESHOLD = 20
    SCS_MOVING_SPEED = 0
    SCS_MOVING_ACC = 0
    protocol_end = 1

    # Initialize PortHandler and PacketHandler
    portHandler = PortHandler(DEVICENAME)
    packetHandler = PacketHandler(protocol_end)

    if not portHandler.openPort():
        print("Failed to open the port")
        return
    if not portHandler.setBaudRate(BAUDRATE):
        print("Failed to change the baudrate")
        return

    # Write SCServo acceleration and speed defaults
    comm_result, error = packetHandler.write1ByteTxRx(portHandler, SCS_ID, ADDR_SCS_GOAL_ACC, SCS_MOVING_ACC)
    if comm_result != COMM_SUCCESS or error != 0:
        print("Error setting goal acceleration")
    comm_result, error = packetHandler.write2ByteTxRx(portHandler, SCS_ID, ADDR_SCS_GOAL_SPEED, SCS_MOVING_SPEED)
    if comm_result != COMM_SUCCESS or error != 0:
        print("Error setting goal speed")

    available_servos = {}
    for servo_id in range(1, 11):
        comm_result, error = packetHandler.ping(portHandler, servo_id)
        if comm_result == COMM_SUCCESS and error == 0:
            available_servos[f"servo{servo_id}"] = f"Servo {servo_id}"
    last_available_time = time.time()

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "TICK":
                current_time = time.time()
                if current_time - last_available_time >= 3:
                    node.send_output(output_id="available_nodes", data=pa.array(list(available_servos.keys())), metadata={})
                    last_available_time = current_time

            elif event["id"] == "set_servo":
                cmd = event["value"].to_py()
                if len(cmd) != 3:
                    print("Invalid set_servo command received")
                    continue
                # Unpack command—ignoring the provided servo_id and using the configured SCS_ID
                _, target_position, target_speed = cmd
                comm_result, error = packetHandler.write2ByteTxRx(portHandler, SCS_ID, ADDR_SCS_GOAL_SPEED, int(target_speed))
                if comm_result != COMM_SUCCESS or error != 0:
                    print("Error setting goal speed:", packetHandler.getTxRxResult(comm_result) if comm_result != COMM_SUCCESS else packetHandler.getRxPacketError(error))
                comm_result, error = packetHandler.write2ByteTxRx(portHandler, SCS_ID, ADDR_SCS_GOAL_POSITION, int(target_position))
                if comm_result != COMM_SUCCESS or error != 0:
                    print("Error setting goal position:", packetHandler.getTxRxResult(comm_result) if comm_result != COMM_SUCCESS else packetHandler.getRxPacketError(error))
                    continue

                while True:
                    present_pos_speed, comm_result, error = packetHandler.read4ByteTxRx(portHandler, SCS_ID, ADDR_SCS_PRESENT_POSITION)
                    if comm_result != COMM_SUCCESS or error != 0:
                        print("Error reading servo position")
                        break
                    present_position = SCS_LOWORD(present_pos_speed)
                    present_speed = SCS_HIWORD(present_pos_speed)
                    print("[ID:%03d] GoalPos:%03d PresPos:%03d PresSpd:%03d" %
                          (SCS_ID, int(target_position), present_position, SCS_TOHOST(present_speed, 15)))
                    if abs(int(target_position) - present_position) <= SCS_MOVING_STATUS_THRESHOLD:
                        break
                    time.sleep(0.1)
                node.send_output(output_id="servo_done", data=pa.array([present_position]), metadata={})

            elif event["id"] == "my_input_id":
                node.send_output(output_id="my_output_id", data=pa.array([1, 2, 3]), metadata={})


if __name__ == "__main__":
    main()
