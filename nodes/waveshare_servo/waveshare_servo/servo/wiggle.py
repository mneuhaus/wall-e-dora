"""Provides the wiggle_servo function for servo identification."""

from __future__ import annotations

import time

from .registers import ADDR_GOAL_POSITION, ADDR_PRESENT_POSITION, ADDR_TORQUE_ENABLE
from .sdk import COMM_SUCCESS



def wiggle_servo(servo, wiggle_range: int = 40, iterations: int = 5) -> bool:
    """Wiggle a servo for identification using the shared SDK connection."""
    try:
        servo_id = servo.id
        ph = servo.port_handler
        pkt = servo.packet_handler
        servo._prepare_port()

        _, result, _ = pkt.ping(ph, servo_id)
        if result != COMM_SUCCESS:
            print(f"Servo ID {servo_id} is not responding to ping")
            return False

        pkt.write1ByteTxRx(ph, servo_id, ADDR_TORQUE_ENABLE, 1)
        current_position, result, error = pkt.read2ByteTxRx(ph, servo_id, ADDR_PRESENT_POSITION)
        if result != COMM_SUCCESS or error != 0:
            print(f"Failed to read position from servo {servo_id}")
            return False

        if current_position == 0:
            current_position = 512

        position_high = min(1023, current_position + wiggle_range)
        position_low = max(0, current_position - wiggle_range)

        for _ in range(iterations):
            pkt.write2ByteTxRx(ph, servo_id, ADDR_GOAL_POSITION, position_high)
            time.sleep(0.35)
            pkt.write2ByteTxRx(ph, servo_id, ADDR_GOAL_POSITION, position_low)
            time.sleep(0.35)

        pkt.write2ByteTxRx(ph, servo_id, ADDR_GOAL_POSITION, current_position)
        time.sleep(0.35)
        pkt.write1ByteTxRx(ph, servo_id, ADDR_TORQUE_ENABLE, 0)
        return True
    except Exception as exc:
        print(f"Error wiggling servo {servo.id}: {exc}")
        return False
