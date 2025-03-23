from dora import Node
import pyarrow as pa
from scservo_sdk import *
import time
import json, os

# Global settings dictionary for caching config values
cached_settings = {
    "unique_id_counter": 10,
    "id_mapping": {},
    "servo_limits": {},  # Store min/max positions for each servo
    "servo_aliases": {},  # Store aliases for servos
    "servo_speeds": {}   # Store preferred speed for each servo
}

# Node reference for sending updates to config
config_node = None

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


def update_config(path, value):
    """Update a setting in the config node"""
    global config_node
    if config_node:
        config_node.send_output(
            output_id="update_setting",
            data=pa.array([{"path": path, "value": value}]),
            metadata={}
        )
        print(f"Sent config update: {path} = {value}")

def main():
    node = Node()
    global config_node, cached_settings
    config_node = node  # Store node reference for config updates
    
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
    
    # Test communication with ping
    ping_result, comm_result, error = packetHandler.ping(portHandler, SCS_ID)
    if comm_result != COMM_SUCCESS or error != 0:
        print(f"Failed to ping servo ID {SCS_ID}")
        print(f"Communication Result: {packetHandler.getTxRxResult(comm_result)}")
        print(f"Error: {packetHandler.getRxPacketError(error)}")
    else:
        print(f"Successfully pinged servo ID {SCS_ID}")

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
        
        try:
            for servo_id in range(1, 21):  # Most servos use IDs 1-20
                try:
                    ping_result, comm_result, error = packetHandler.ping(portHandler, servo_id)
                    if comm_result == COMM_SUCCESS and error == 0:
                        if servo_id == 1:
                            try:
                                new_id = cached_settings["unique_id_counter"]
                                portHandler.closePort()
                                change_servo_id(DEVICENAME, 1, new_id, BAUDRATE)
                                if not portHandler.openPort():
                                    print("Failed to reopen the port after id change")
                                cached_settings["unique_id_counter"] += 1
                                # Update config with new counter value
                                update_config("servo_settings.unique_id_counter", cached_settings["unique_id_counter"])
                                print(f"Updated servo id 1 to {new_id}")
                                servo_id = new_id
                            except Exception as e:
                                print(f"Error changing servo ID: {e}")
                                # Continue with original ID if there was an error
        
                        # Read current servo status
                        try:
                            pos_data, pos_result, pos_error = packetHandler.read2ByteTxRx(
                                portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
                            )
                            speed_data, speed_result, speed_error = packetHandler.read2ByteTxRx(
                                portHandler, servo_id, 57  # Present speed register
                            )
                            torque_data, torque_result, torque_error = packetHandler.read2ByteTxRx(
                                portHandler, servo_id, 60  # Present load (torque) register
                            )
        
                            # Get the saved speed setting (or default to current speed)
                            saved_speed = cached_settings.get("servo_speeds", {}).get(str(servo_id), 
                                speed_data if speed_result == COMM_SUCCESS and speed_error == 0 else 200)
                            
                            servo_data = {
                                "id": servo_id,
                                "position": pos_data if pos_result == COMM_SUCCESS and pos_error == 0 else 0,
                                "speed": saved_speed,  # Use the saved speed from settings
                                "torque": torque_data if torque_result == COMM_SUCCESS and torque_error == 0 else 0,
                                "alias": cached_settings.get("servo_aliases", {}).get(str(servo_id), "")
                            }
                            
                            # Add calibration data if available
                            if str(servo_id) in cached_settings.get("servo_limits", {}):
                                servo_data["min_pos"] = cached_settings["servo_limits"][str(servo_id)]["min"]
                                servo_data["max_pos"] = cached_settings["servo_limits"][str(servo_id)]["max"]
                            
                            available_servos.append(servo_data)
                        except Exception as e:
                            print(f"Error reading servo {servo_id} data: {e}")
                except Exception as e:
                    print(f"Error pinging servo {servo_id}: {e}")
        except Exception as e:
            print(f"Error during servo scan: {e}")
        
        print(f"Available servos found: {[s['id'] for s in available_servos]}")
        
        # If no servos found, use fallback data from settings
        if not available_servos and cached_settings.get("servo_limits"):
            print("No servos found, using fallback data from settings")
            for servo_id, limits in cached_settings.get("servo_limits", {}).items():
                try:
                    servo_id = int(servo_id)
                    # Get saved speed or use default
                    saved_speed = cached_settings.get("servo_speeds", {}).get(str(servo_id), 200)
                    
                    fallback_data = {
                        "id": servo_id,
                        "position": 500,
                        "speed": saved_speed,  # Use the saved speed from settings
                        "torque": 0,
                        "min_pos": limits["min"],
                        "max_pos": limits["max"],
                        "alias": cached_settings.get("servo_aliases", {}).get(str(servo_id), ""),
                        "is_fallback": True
                    }
                    available_servos.append(fallback_data)
                except Exception as e:
                    print(f"Error creating fallback data for servo {servo_id}: {e}")
        
        node.send_output(output_id="servo_status", data=pa.array(available_servos), metadata={})
    
    def handle_set_servo_event(event):
        cmd = event["value"].to_pylist()
        if len(cmd) < 2:
            print("Invalid set_servo command received")
            return
            
        # Check if speed is provided
        if len(cmd) == 3:
            servo_id, target_position, target_speed = cmd
        else:
            # Use saved speed if not provided
            servo_id, target_position = cmd
            # Get the saved speed setting or default to 200
            target_speed = settings.get("servo_speeds", {}).get(str(servo_id), 200)
        
        # Convert to integers
        servo_id = int(servo_id)
        target_position = int(target_position)
        target_speed = int(target_speed)
        
        # Check if this servo has calibration limits and apply them
        if str(servo_id) in settings.get("servo_limits", {}):
            min_pos = settings["servo_limits"][str(servo_id)]["min"]
            max_pos = settings["servo_limits"][str(servo_id)]["max"]
            # Constrain target position to the calibrated range
            target_position = max(min_pos, min(max_pos, target_position))
        else:
            # Default safe range if no calibration exists
            target_position = max(0, min(4095, target_position))
            
        # Ensure speed is in a safe range (lower is safer)
        target_speed = min(target_speed, 500)  # Cap speed at 500 to prevent overload
        
        # Get current position first to avoid sudden large movements
        try:
            pos_data, pos_result, pos_error = packetHandler.read2ByteTxRx(
                portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
            )
            
            # If we could read the current position, check if target is too far
            if pos_result == COMM_SUCCESS and pos_error == 0:
                current_pos = pos_data
                # If target is too far from current position, move in smaller steps
                if abs(target_position - current_pos) > 500:
                    print(f"Target position {target_position} too far from current position {current_pos}. Moving incrementally.")
                    # Use a much lower speed for large movements
                    safe_speed = min(target_speed, 200)
                    # Set the safe speed
                    packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, safe_speed)
                    # Move halfway first
                    halfway_pos = current_pos + (target_position - current_pos) // 2
                    packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, halfway_pos)
                    time.sleep(0.5)  # Give servo time to reach halfway
        except Exception as e:
            print(f"Error reading current position: {e}")
            
        print(f"Setting servo {servo_id} to position {target_position} at speed {target_speed}")
        
        # Try to recover from overload first by using a very low speed and moving to current position
        try:
            # Use extremely low speed to "unstick" servos
            recovery_speed = 50
            comm_result, error = packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, recovery_speed)
            if comm_result != COMM_SUCCESS or error != 0:
                error_msg = packetHandler.getRxPacketError(error) if error != 0 else packetHandler.getTxRxResult(comm_result)
                if "Overload" in str(error_msg):
                    print(f"Servo {servo_id} is overloaded. Attempting recovery...")
                    # Try to turn off torque to clear overload (may not work for all servos)
                    packetHandler.write1ByteTxRx(portHandler, servo_id, 40, 0)  # 40 is torque enable register
                    time.sleep(0.5)  # Give servo time to relax
                    packetHandler.write1ByteTxRx(portHandler, servo_id, 40, 1)  # Turn torque back on
                    time.sleep(0.3)  # Wait a moment
        except Exception as e:
            print(f"Servo recovery attempt error: {e}")
        
        # Try several attempts with increasing speeds
        for attempt_speed in [300, target_speed]:
            try:
                # Apply speed first
                comm_result, error = packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, attempt_speed)
                if comm_result != COMM_SUCCESS or error != 0:
                    error_msg = packetHandler.getRxPacketError(error) if error != 0 else packetHandler.getTxRxResult(comm_result)
                    print(f"Error setting goal speed to {attempt_speed}: {error_msg}")
                    continue  # Try next speed
                
                # Then apply position
                comm_result, error = packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, target_position)
                if comm_result != COMM_SUCCESS or error != 0:
                    error_msg = packetHandler.getRxPacketError(error) if error != 0 else packetHandler.getTxRxResult(comm_result)
                    print(f"Error setting goal position to {target_position}: {error_msg}")
                    continue  # Try next speed
                
                # If we got here, it worked!
                print(f"Successfully set servo {servo_id} position to {target_position} at speed {attempt_speed}")
                return
            except Exception as e:
                print(f"Attempt error with speed {attempt_speed}: {e}")
        
        print(f"Failed to set servo {servo_id} after all attempts")
    
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
        print(f"Calibrating servo {servo_id}")
        
        # Set a slow speed for calibration
        slow_speed = 100
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, slow_speed)
        
        # Step 1: Move to minimum position
        MIN_POS = SCS_MINIMUM_POSITION_VALUE
        print(f"Moving to minimum calibrated position...")
        
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, MIN_POS)
        time.sleep(3.0)  # Increased wait time for reliable movement
        
        # Read the actual position achieved
        min_pos_data, min_pos_result, min_pos_error = packetHandler.read2ByteTxRx(
            portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
        )
        
        if min_pos_result != COMM_SUCCESS or min_pos_error != 0:
            print("Failed to read minimum position")
            min_pos_data = MIN_POS
        
        # Step 2: Move to maximum position
        MAX_POS = SCS_MAXIMUM_POSITION_VALUE
        print(f"Moving to maximum calibrated position...")
        
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, MAX_POS)
        time.sleep(3.0)  # Increased waiting time
        
        # Read the actual position achieved
        max_pos_data, max_pos_result, max_pos_error = packetHandler.read2ByteTxRx(
            portHandler, servo_id, ADDR_SCS_PRESENT_POSITION
        )
        
        if max_pos_result != COMM_SUCCESS or max_pos_error != 0:
            print("Failed to read maximum position")
            max_pos_data = MAX_POS
            
        # Step 3: Move back to center position
        MID_POS = (min_pos_data + max_pos_data) // 2
        print(f"Moving to center position...")
        
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, MID_POS)
        time.sleep(1.0)  # Give servo time to reach position
        
        # Step 4: Save the calibration data
        print(f"Saving calibration: min={min_pos_data}, max={max_pos_data}")
        
        # Update local cache
        cached_settings.setdefault("servo_limits", {})
        cached_settings["servo_limits"][str(servo_id)] = {
            "min": min_pos_data,
            "max": max_pos_data
        }
        
        # Update config (using 0-based index in config)
        update_config(f"servo.{servo_id - 1}.min", min_pos_data)
        update_config(f"servo.{servo_id - 1}.max", max_pos_data)
        
        # Set a safe speed for this servo if not already set
        if str(servo_id) not in cached_settings.get("servo_speeds", {}):
            cached_settings.setdefault("servo_speeds", {})
            cached_settings["servo_speeds"][str(servo_id)] = 200
            update_config(f"servo.{servo_id - 1}.speed", 200)
        
        print(f"Calibration complete for servo {servo_id}.")
        print(f"Measured servo range: {min_pos_data}-{max_pos_data}")
        print(f"Servo is now at center position {MID_POS}")
        
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
        
        # Update local cache
        cached_settings.setdefault("servo_speeds", {})
        cached_settings["servo_speeds"][str(servo_id)] = target_speed
        
        # Update config (using 0-based index in config)
        update_config(f"servo.{servo_id - 1}.speed", target_speed)
        
        # Apply the speed to the current servo state
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
    
    def handle_reset_servo_event(event):
        servo_id = event["value"].to_pylist()[0]
        print(f"Resetting servo {servo_id} to default settings")
        
        # Remove servo limits from local cache
        if str(servo_id) in cached_settings.get("servo_limits", {}):
            del cached_settings["servo_limits"][str(servo_id)]
            print(f"Removed calibration settings for servo {servo_id}")
            
        # Remove alias if present 
        if str(servo_id) in cached_settings.get("servo_aliases", {}):
            del cached_settings["servo_aliases"][str(servo_id)]
            print(f"Removed alias for servo {servo_id}")
        
        # Update config to remove settings (0-based index)
        # Set default values instead of deleting to maintain the structure
        update_config(f"servo.{servo_id - 1}", {
            "id": servo_id,
            "alias": "",
            "min": 0,
            "max": 4095,
            "speed": 0,
            "reset": True  # Flag to indicate this servo was reset
        })
        
        # Reset servo to factory defaults
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_SPEED, 0)  # Default speed
        
        # Move to center position
        packetHandler.write2ByteTxRx(portHandler, servo_id, ADDR_SCS_GOAL_POSITION, 2048)
        
        print(f"Reset servo {servo_id} to factory defaults")
        handle_scan_event()  # Update UI with reset status
    
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
            elif event["id"] == "reset_servo":
                handle_reset_servo_event(event)
            elif event["id"] == "set_alias":
                data = event["value"].to_pylist()
                if len(data) == 2:
                    servo_id, alias = data
                    
                    # Update local cache for immediate use
                    cached_settings.setdefault("servo_aliases", {})
                    cached_settings["servo_aliases"][str(servo_id)] = alias
                    
                    # Update config node (using 0-based index in config)
                    update_config(f"servo.{servo_id - 1}.alias", alias)
                    
                    print(f"Set alias for servo {servo_id} to {alias}")
                    handle_scan_event()  # Update UI with new alias
            elif event["id"] == "setting_updated":
                try:
                    # Handle config change events
                    setting_data = event["value"].to_pylist()[0]
                    path = setting_data.get("path", "")
                    value = setting_data.get("value", None)
                    
                    # Check if it's a servo alias update
                    if path.startswith("servo.") and path.endswith(".alias") and value is not None:
                        # Extract servo index from the path (e.g., "servo.0.alias" -> 0)
                        parts = path.split(".")
                        if len(parts) == 3 and parts[1].isdigit():
                            servo_index = int(parts[1])
                            # Servo IDs are 1-based, but config indices are 0-based
                            servo_id = servo_index + 1
                            
                            # Update the alias in our local cache
                            cached_settings.setdefault("servo_aliases", {})
                            cached_settings["servo_aliases"][str(servo_id)] = value
                            print(f"Updated servo {servo_id} alias to '{value}' from config")
                            handle_scan_event()  # Update UI with new settings
                    
                    # Handle servo speed settings
                    elif path.startswith("servo.") and path.endswith(".speed") and value is not None:
                        parts = path.split(".")
                        if len(parts) == 3 and parts[1].isdigit():
                            servo_index = int(parts[1])
                            servo_id = servo_index + 1
                            
                            # Update the speed in our local cache
                            cached_settings.setdefault("servo_speeds", {})
                            cached_settings["servo_speeds"][str(servo_id)] = value
                            print(f"Updated servo {servo_id} speed to {value} from config")
                            handle_scan_event()
                    
                    # Handle servo limits settings
                    elif path.startswith("servo.") and (path.endswith(".min") or path.endswith(".max")) and value is not None:
                        parts = path.split(".")
                        if len(parts) == 3 and parts[1].isdigit():
                            servo_index = int(parts[1])
                            servo_id = servo_index + 1
                            limit_type = parts[2]  # "min" or "max"
                            
                            # Update the limit in our local cache
                            cached_settings.setdefault("servo_limits", {})
                            cached_settings["servo_limits"].setdefault(str(servo_id), {})
                            cached_settings["servo_limits"][str(servo_id)][limit_type] = value
                            print(f"Updated servo {servo_id} {limit_type} limit to {value} from config")
                            handle_scan_event()
                    
                    # Handle settings object if received as a whole
                    elif path == "settings" and isinstance(value, dict):
                        # Update our entire cached settings
                        for key, val in value.items():
                            cached_settings[key] = val
                        print("Updated all servo settings from config")
                        handle_scan_event()
                except Exception as e:
                    print(f"Error processing config setting_updated: {e}")

if __name__ == "__main__":
    main()
