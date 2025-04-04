"""Provides the wiggle_servo function for servo identification."""

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


def wiggle_servo(servo, wiggle_range: int = 40, iterations: int = 5) -> bool:
    """Wiggle a servo for identification using the SDK.

    Moves the servo back and forth around its current position to help
    physically identify it. Reads the current position, calculates target
    positions based on `wiggle_range`, enables torque, performs the wiggle
    motion for the specified `iterations`, restores the original position,
    and disables torque.

    Args:
        servo: The `Servo` object to wiggle.
        wiggle_range: The number of position steps to move in each direction
                      from the current position (default: 40).
        iterations: The number of back-and-forth wiggle cycles to perform
                    (default: 5).

    Returns:
        True if the wiggle sequence completed successfully, False otherwise.
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
