"""Provides the wiggle_servo function for servo identification."""

import time
from .sdk import COMM_SUCCESS

# Control table addresses for SCS servos
ADDR_SCS_TORQUE_ENABLE = 40
ADDR_SCS_GOAL_POSITION = 42
ADDR_SCS_PRESENT_POSITION = 56


def wiggle_servo(servo, wiggle_range: int = 40, iterations: int = 5) -> bool:
    """Wiggle a servo for identification using the shared SDK connection.

    Args:
        servo: The Servo object to wiggle.
        wiggle_range: Position steps to move in each direction (default: 40).
        iterations: Number of back-and-forth cycles (default: 5).

    Returns:
        True if the wiggle sequence completed successfully, False otherwise.
    """
    try:
        servo_id = servo.id
        ph = servo.port_handler
        pkt = servo.packet_handler
        print(f"Wiggling servo {servo_id}")

        # Ping to verify responsiveness
        model_num, result, error = pkt.ping(ph, servo_id)
        if result != COMM_SUCCESS or error != 0:
            print(f"Servo ID {servo_id} is not responding to ping!")
            return False

        # Enable torque
        result, error = pkt.write1ByteTxRx(ph, servo_id, ADDR_SCS_TORQUE_ENABLE, 1)
        if result != COMM_SUCCESS or error != 0:
            print(f"Failed to enable torque on servo {servo_id}")
            return False

        # Read current position
        current_position, result, error = pkt.read2ByteTxRx(
            ph, servo_id, ADDR_SCS_PRESENT_POSITION
        )
        if result != COMM_SUCCESS or error != 0:
            print(f"Failed to read position from servo {servo_id}")
            return False

        if current_position == 0:
            current_position = 512

        position_high = current_position + wiggle_range
        position_low = current_position - wiggle_range

        # Perform wiggle
        for i in range(iterations):
            pkt.write2ByteTxRx(ph, servo_id, ADDR_SCS_GOAL_POSITION, position_high)
            time.sleep(0.5)
            pkt.write2ByteTxRx(ph, servo_id, ADDR_SCS_GOAL_POSITION, position_low)
            time.sleep(0.5)

        # Restore original position
        pkt.write2ByteTxRx(ph, servo_id, ADDR_SCS_GOAL_POSITION, current_position)
        time.sleep(0.5)

        # Disable torque
        pkt.write1ByteTxRx(ph, servo_id, ADDR_SCS_TORQUE_ENABLE, 0)

        print(f"Wiggle complete for servo {servo_id}")
        return True

    except Exception as e:
        print(f"Error wiggling servo {servo.id}: {e}")
        return False
