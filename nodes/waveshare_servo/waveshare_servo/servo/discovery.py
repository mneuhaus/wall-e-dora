"""Servo discovery utility for the Waveshare Servo Node."""

from typing import Set

from .sdk import COMM_SUCCESS

# Error bits that indicate the servo is overloaded/stressed but still responsive
# We still want to discover these servos
ERRBIT_OVERLOAD = 32


def discover_servos(port_handler, packet_handler) -> Set[int]:
    """Discover connected servos by pinging a range of possible IDs.

    A servo is considered discovered if the ping communication succeeds,
    even if the servo reports non-fatal error flags (like overload).

    Args:
        port_handler: An open SDK PortHandler instance.
        packet_handler: An SDK PacketHandler instance.

    Returns:
        A set containing the IDs of the servos that responded to the ping.
    """
    if not port_handler or not port_handler.is_open:
        print("Discovery: port not open")
        return set()

    try:
        if not port_handler.ser or not port_handler.ser.is_open:
            print("Discovery: underlying serial closed")
            return set()
        port_handler.ser.reset_input_buffer()
        port_handler.is_using = False
    except Exception as e:
        print(f"Discovery: pre-scan cleanup failed: {e}")
        return set()

    discovered_servos = set()

    for servo_id in range(1, 16):
        try:
            port_handler.is_using = False
            model_num, result, error = packet_handler.ping(port_handler, servo_id)
            if result == COMM_SUCCESS:
                # Servo responded - consider it discovered regardless of error flags
                # Error flags (overload, overheat, etc.) mean the servo has issues
                # but is still physically connected and communicating
                discovered_servos.add(servo_id)
        except Exception as e:
            print(f"Error while pinging servo {servo_id}: {e}")
            port_handler.is_using = False

    return discovered_servos
