from dora import Node
import pyarrow as pa
from scservo_sdk import *
import time
import json, os
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "servo_settings.json")

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {"unique_id_counter": 10, "id_mapping": {}}
    return settings

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)

def change_servo_id(serial_port, old_id, new_id, baudrate=1000000):
    """
    Change the ID of an SCS servo by unlocking EPROM, changing the ID, and locking EPROM.
    
    :param serial_port: Serial port name (e.g., '/dev/ttyUSB0')
    :param old_id: Current ID of the servo (factory default is 1)
    :param new_id: New ID to assign to the servo
    :param baudrate: Baud rate (default: 1000000)
    """
    # Constants for SCS servo registers (assumed values)
    SCSCL_ID = 3
    SCSCL_LOCK = 47

    try:
        import serial
        ser = serial.Serial(serial_port, baudrate, timeout=1)
        time.sleep(0.1)
        
        # Unlock EPROM (set LOCK register to 0)
        unlock_cmd = [0xFF, 0xFF, old_id, 4, 3, SCSCL_LOCK, 0]
        unlock_checksum = (~sum(unlock_cmd[2:]) & 0xFF)
        unlock_cmd.append(unlock_checksum)
        ser.write(bytearray(unlock_cmd))
        time.sleep(0.1)
        
        # Change servo ID (write new_id to SCSCL_ID register)
        change_cmd = [0xFF, 0xFF, old_id, 4, 3, SCSCL_ID, new_id]
        change_checksum = (~sum(change_cmd[2:]) & 0xFF)
        change_cmd.append(change_checksum)
        ser.write(bytearray(change_cmd))
        time.sleep(0.1)
        
        # Lock EPROM (set LOCK register to 1 on new ID)
        lock_cmd = [0xFF, 0xFF, new_id, 4, 3, SCSCL_LOCK, 1]
        lock_checksum = (~sum(lock_cmd[2:]) & 0xFF)
        lock_cmd.append(lock_checksum)
        ser.write(bytearray(lock_cmd))
        time.sleep(0.1)
        
        print(f"Changed servo ID from {old_id} to {new_id}")
        ser.close()
    except Exception as e:
        print(f"Error: {e}")

def main():
    node = Node()
    # SCServo configuration
    DEVICENAME = '/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FD016638-if00'
    BAUDRATE = 1000000
    settings = load_settings()
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
        print("Error setting goal speed (default)")

    last_available_time = time.time()

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "SCAN":
                print("Scan event triggered")
                current_time = time.time()
                if current_time - last_available_time >= 3:
                    available_servos = {}
                    for servo_id in range(1, 11):
                        ping_result, comm_result, error = packetHandler.ping(portHandler, servo_id)
                        if comm_result == COMM_SUCCESS and error == 0:
                            if servo_id == 1:
                                new_id = settings["unique_id_counter"]
                                # Close the port before issuing the ID change command.
                                portHandler.closePort()
                                change_servo_id(DEVICENAME, 1, new_id, BAUDRATE)
                                # Reopen the port after changing the ID.
                                if not portHandler.openPort():
                                    print("Failed to reopen the port after id change")
                                settings["unique_id_counter"] += 1
                                save_settings(settings)
                                print(f"Updated servo id 1 to {new_id}")
                                servo_id = new_id
                            available_servos[f"servo{servo_id}"] = f"Servo {servo_id}"
                    print(f"Available servos found: {available_servos}")
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
                    print(f"Error setting goal speed: {packetHandler.getTxRxResult(comm_result) if comm_result != COMM_SUCCESS else packetHandler.getRxPacketError(error)}")
                comm_result, error = packetHandler.write2ByteTxRx(portHandler, SCS_ID, ADDR_SCS_GOAL_POSITION, int(target_position))
                if comm_result != COMM_SUCCESS or error != 0:
                    print(f"Error setting goal position: {packetHandler.getTxRxResult(comm_result) if comm_result != COMM_SUCCESS else packetHandler.getRxPacketError(error)}")
                node.send_output(output_id="servo_done", data=pa.array([int(target_position)]), metadata={})

            elif event["id"] == "my_input_id":
                node.send_output(output_id="my_output_id", data=pa.array([1, 2, 3]), metadata={})

if __name__ == "__main__":
    main()
