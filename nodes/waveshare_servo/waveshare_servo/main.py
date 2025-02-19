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
        settings = {
            "unique_id_counter": 10,
            "id_mapping": {},
            "servo_limits": {},  # Store min/max positions for each servo
            "servo_aliases": {}  # Store aliases for servos
        }
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
    SCSCL_ID = 5
    SCSCL_LOCK = 48

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
    
    def handle_scan_event():
        available_servos = []
        # Only scan reasonable ID range and use shorter timeout
        portHandler.setPacketTimeout(5)  # 5ms timeout instead of default
        
        for servo_id in range(1, 21):  # Most servos use IDs 1-20
            ping_result, comm_result, error = packetHandler.ping(portHandler, servo_id)
            if comm_result == COMM_SUCCESS and error == 0:
                if servo_id == 1:
                    new_id = settings["unique_id_counter"]
                    portHandler.closePort()
                    change_servo_id(DEVICENAME, 1, new_id, BAUDRATE)
                    if not portHandler.openPort():
                        print("Failed to reopen the port after id change")
                    settings["unique_id_counter"] += 1
                    save_settings(settings)
                    print(f"Updated servo id 1 to {new_id}")
                    servo_id = new_id

                # Read current servo status
                pos_data, pos_result, pos_error = packetHandler.read2ByteTxRx(
                    portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
                )
                speed_data, speed_result, speed_error = packetHandler.read2ByteTxRx(
                    portHandler, servo_id, 57  # Present speed register
                )
                torque_data, torque_result, torque_error = packetHandler.read2ByteTxRx(
                    portHandler, servo_id, 60  # Present load (torque) register
                )

                servo_data = {
                    "id": servo_id,
                    "position": pos_data if pos_result == COMM_SUCCESS and pos_error == 0 else 0,
                    "speed": speed_data if speed_result == COMM_SUCCESS and speed_error == 0 else 0,
                    "torque": torque_data if torque_result == COMM_SUCCESS and torque_error == 0 else 0,
                    "alias": settings.get("servo_aliases", {}).get(str(servo_id), "")
                }
                
                # Add calibration data if available
                if str(servo_id) in settings.get("servo_limits", {}):
                    servo_data["min_pos"] = settings["servo_limits"][str(servo_id)]["min"]
                    servo_data["max_pos"] = settings["servo_limits"][str(servo_id)]["max"]
                
                available_servos.append(servo_data)
        
        print(f"Available servos found: {[s['id'] for s in available_servos]}")
        node.send_output(output_id="servo_status", data=pa.array(available_servos), metadata={})
    
    def handle_set_servo_event(event):
        cmd = event["value"].to_pylist()
        if len(cmd) != 3:
            print("Invalid set_servo command received")
            return
        # Unpack command using the provided servo_id
        servo_id, target_position, target_speed = cmd
        print(f"Setting servo {servo_id} to position {target_position} at speed {target_speed}")
        
        comm_result, error = packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, int(target_speed))
        if comm_result != COMM_SUCCESS or error != 0:
            print(f"Error setting goal speed: {packetHandler.getTxRxResult(comm_result) if comm_result != COMM_SUCCESS else packetHandler.getRxPacketError(error)}")
            return
            
        comm_result, error = packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, int(target_position))
        if comm_result != COMM_SUCCESS or error != 0:
            print(f"Error setting goal position: {packetHandler.getTxRxResult(comm_result) if comm_result != COMM_SUCCESS else packetHandler.getRxPacketError(error)}")
            return
            
        print(f"Successfully set servo {servo_id} position and speed")
    
    def handle_change_servo_id_event(event):
        data = event["value"].to_pylist()
        if (not isinstance(data, list)) or (len(data) != 2):
            print("Invalid change_servo_id command received")
            return
        old_id, new_id = data
        portHandler.closePort()
        change_servo_id(DEVICENAME, old_id, new_id, BAUDRATE)
        if not portHandler.openPort():
            print("Failed to reopen the port after ID change")
        print(f"Changed servo ID from {old_id} to {new_id}")
        nonlocal SCS_ID
        if SCS_ID == old_id:
            SCS_ID = new_id
    
    def handle_calibrate_event(event):
        servo_id = event["value"].to_pylist()[0]
        print(f"Starting calibration for servo {servo_id}")
        
        # Start from current position
        pos_data, pos_result, pos_error = packetHandler.read2ByteTxRx(
            portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
        )
        if pos_result != COMM_SUCCESS or pos_error != 0:
            print("Failed to read current position")
            return
        
        # Set slow speed for calibration
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, 100)
        
        # Find minimum position
        min_pos = pos_data
        while True:
            test_pos = min_pos - 50
            packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, test_pos)
            time.sleep(0.5)  # Wait for movement
            
            actual_pos, pos_result, pos_error = packetHandler.read2ByteTxRx(
                portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
            )
            if abs(actual_pos - min_pos) < 10:  # If barely moved, we found the limit
                break
            min_pos = actual_pos
        
        # Find maximum position
        max_pos = pos_data
        while True:
            test_pos = max_pos + 50
            packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, test_pos)
            time.sleep(0.5)  # Wait for movement
            
            actual_pos, pos_result, pos_error = packetHandler.read2ByteTxRx(
                portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
            )
            if abs(actual_pos - max_pos) < 10:  # If barely moved, we found the limit
                break
            max_pos = actual_pos
        
        # Save calibration to settings
        settings.setdefault("servo_limits", {})
        settings["servo_limits"][str(servo_id)] = {
            "min": min_pos,
            "max": max_pos
        }
        save_settings(settings)
        
        # Return to center position
        center_pos = min_pos + (max_pos - min_pos) // 2
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, center_pos)
        
        print(f"Calibration complete for servo {servo_id}. Range: {min_pos}-{max_pos}")
        
        # Trigger a scan to update the UI with new calibration data
        handle_scan_event()

    def handle_set_speed_event(event):
        cmd = event["value"].to_pylist()
        if len(cmd) != 2:
            print("Invalid set_speed command received")
            return
        # Unpack command using the provided servo_id and speed
        servo_id, target_speed = cmd
        print(f"Setting servo {servo_id} speed to {target_speed}")
        
        # Ensure speed is within valid range (100-2000)
        target_speed = max(100, min(2000, int(target_speed)))
        
        comm_result, error = packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, target_speed)
        if comm_result != COMM_SUCCESS or error != 0:
            print(f"Error setting goal speed: {packetHandler.getTxRxResult(comm_result) if comm_result != COMM_SUCCESS else packetHandler.getRxPacketError(error)}")
            return
            
        print(f"Successfully set servo {servo_id} speed to {target_speed}")
        
        # Trigger a scan to update the UI with new speed
        handle_scan_event()

    def handle_wiggle_event(event):
        servo_id = event["value"].to_pylist()[0]
        # Read current position
        pos_data, pos_result, pos_error = packetHandler.read2ByteTxRx(
            portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
        )
        if pos_result != COMM_SUCCESS or pos_error != 0:
            print("Failed to read current position")
            return
            
        center_pos = pos_data
        wiggle_amount = 50  # ~5 degrees
        speed = 400
        
        # Set speed
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, speed)
        
        # Wiggle 3 times
        for _ in range(3):
            # Move right
            packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, center_pos + wiggle_amount)
            time.sleep(0.3)
            # Move left
            packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, center_pos - wiggle_amount)
            time.sleep(0.3)
        
        # Return to center
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, center_pos)
    
    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "SCAN":
                handle_scan_event()
            elif event["id"] == "set_servo":
                handle_set_servo_event(event)
            elif event["id"] == "change_servo_id":
                handle_change_servo_id_event(event)
            elif event["id"] == "wiggle":
                handle_wiggle_event(event)
            elif event["id"] == "calibrate":
                handle_calibrate_event(event)
            elif event["id"] == "set_speed":
                handle_set_speed_event(event)
            elif event["id"] == "set_alias":
                data = event["value"].to_pylist()
                if len(data) == 2:
                    servo_id, alias = data
                    settings.setdefault("servo_aliases", {})
                    settings["servo_aliases"][str(servo_id)] = alias
                    save_settings(settings)
                    print(f"Set alias for servo {servo_id} to {alias}")
                    handle_scan_event()  # Update UI with new alias

if __name__ == "__main__":
    main()
