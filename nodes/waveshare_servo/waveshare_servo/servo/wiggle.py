"""
Wiggle operation for servo identification.
"""

import time
from .sdk import (
    PortHandler, 
    PacketHandler, 
    COMM_SUCCESS
)

# Control table addresses for SCS servos
ADDR_SCS_TORQUE_ENABLE = 40
ADDR_SCS_GOAL_POSITION = 42
ADDR_SCS_PRESENT_POSITION = 56

# Default device settings
BAUDRATE = 1000000
PROTOCOL_END = 1  # Using protocol_end = 1


def wiggle_servo(servo, wiggle_range=40, iterations=5):
    """
    Wiggle a servo for identification by moving it back and forth by approximately 3% of rotation.
    
    This function uses the direct SDK approach to interact with the servo hardware.
    
    Args:
        servo: The servo object to wiggle
        wiggle_range: The number of steps to move in each direction (default: 40 - approx 3% of rotation)
        iterations: Number of times to complete the wiggle pattern
        
    Returns:
        bool: True if wiggle was successful, False otherwise
    """
    try:
        servo_id = servo.id
        print(f"Wiggling servo {servo_id}")
        
        # Initialize SDK classes for direct control
        # Get the port path from the serial_conn object
        device_name = servo.serial_conn.port
        port_handler = PortHandler(device_name)
        packet_handler = PacketHandler(PROTOCOL_END)
        
        # Open port
        if not port_handler.openPort():
            print("Failed to open the port.")
            return False

        if not port_handler.setBaudRate(BAUDRATE):
            print("Failed to set baudrate.")
            port_handler.closePort()
            return False
            
        # Ping the servo to verify it's responsive
        print(f"Pinging servo ID {servo_id}...")
        model_num, result, error = packet_handler.ping(port_handler, servo_id)
        if result != COMM_SUCCESS or error != 0:
            print(f"Servo ID {servo_id} is not responding to ping!")
            port_handler.closePort()
            return False
        print(f"Servo ID {servo_id} responded to ping. Model number: {model_num}")
        
        # Ensure torque is enabled
        print(f"Enabling torque on servo ID {servo_id}...")
        scs_comm_result, scs_error = packet_handler.write1ByteTxRx(
            port_handler, servo_id, ADDR_SCS_TORQUE_ENABLE, 1
        )
        
        if scs_comm_result != COMM_SUCCESS or scs_error != 0:
            print(f"Failed to enable torque on servo ID {servo_id}.")
            print(f"  - Result: {packet_handler.getTxRxResult(scs_comm_result)}")
            if scs_error != 0:
                print(f"  - Error: {packet_handler.getRxPacketError(scs_error)}")
            port_handler.closePort()
            return False
        
        # Read current position
        print(f"Reading current position from servo ID {servo_id}...")
        current_position, scs_comm_result, scs_error = packet_handler.read2ByteTxRx(
            port_handler, servo_id, ADDR_SCS_PRESENT_POSITION
        )
        
        if scs_comm_result != COMM_SUCCESS or scs_error != 0:
            print(f"Failed to read the current position from servo ID {servo_id}.")
            print(f"  - Result: {packet_handler.getTxRxResult(scs_comm_result)}")
            if scs_error != 0:
                print(f"  - Error: {packet_handler.getRxPacketError(scs_error)}")
            port_handler.closePort()
            return False
        
        print(f"Current position: {current_position}")
        
        # If position read is 0, use middle position as fallback
        if current_position == 0:
            current_position = 512  # Middle position (1023/2) for these servos
            print(f"Using default middle position: {current_position}")
        
        # Define target positions for wiggle
        position_high = current_position + wiggle_range
        position_low = current_position - wiggle_range
        
        # Perform wiggle pattern
        for i in range(iterations):
            print(f"Cycle {i+1}: Moving to position {position_high}")
            scs_comm_result, scs_error = packet_handler.write2ByteTxRx(
                port_handler, servo_id, ADDR_SCS_GOAL_POSITION, position_high
            )
            
            if scs_comm_result != COMM_SUCCESS or scs_error != 0:
                print(f"Failed to set position {position_high}.")
                print(f"  - Result: {packet_handler.getTxRxResult(scs_comm_result)}")
                if scs_error != 0:
                    print(f"  - Error: {packet_handler.getRxPacketError(scs_error)}")
            time.sleep(0.5)  # Wait for movement
            
            print(f"Cycle {i+1}: Moving to position {position_low}")
            scs_comm_result, scs_error = packet_handler.write2ByteTxRx(
                port_handler, servo_id, ADDR_SCS_GOAL_POSITION, position_low
            )
            
            if scs_comm_result != COMM_SUCCESS or scs_error != 0:
                print(f"Failed to set position {position_low}.")
                print(f"  - Result: {packet_handler.getTxRxResult(scs_comm_result)}")
                if scs_error != 0:
                    print(f"  - Error: {packet_handler.getRxPacketError(scs_error)}")
            time.sleep(0.5)  # Wait for movement
        
        # Restore servo to original position
        print(f"Restoring servo to original position {current_position}")
        scs_comm_result, scs_error = packet_handler.write2ByteTxRx(
            port_handler, servo_id, ADDR_SCS_GOAL_POSITION, current_position
        )
        
        if scs_comm_result != COMM_SUCCESS or scs_error != 0:
            print(f"Failed to restore original position.")
            print(f"  - Result: {packet_handler.getTxRxResult(scs_comm_result)}")
            if scs_error != 0:
                print(f"  - Error: {packet_handler.getRxPacketError(scs_error)}")
        time.sleep(0.5)  # Wait for movement to complete
        
        # Disable torque
        print(f"Disabling torque on servo ID {servo_id}...")
        scs_comm_result, scs_error = packet_handler.write1ByteTxRx(
            port_handler, servo_id, ADDR_SCS_TORQUE_ENABLE, 0
        )
        if scs_comm_result != COMM_SUCCESS or scs_error != 0:
            print(f"Failed to disable torque.")
            print(f"  - Result: {packet_handler.getTxRxResult(scs_comm_result)}")
            if scs_error != 0:
                print(f"  - Error: {packet_handler.getRxPacketError(scs_error)}")
        
        # Clean up
        port_handler.closePort()
        print(f"Wiggle complete for servo {servo_id}")
        return True
    
    except Exception as e:
        print(f"Error wiggling servo {servo.id}: {e}")
        try:
            # Try to close the port if it's still open
            if 'port_handler' in locals() and port_handler.isOpen():
                port_handler.closePort()
        except:
            pass
        return False