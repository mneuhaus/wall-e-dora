"""
Servo discovery utilities for the Waveshare Servo Node.
"""

import time
from typing import Set


def discover_servos(serial_conn) -> Set[int]:
    """Discover all connected servos."""
    if not serial_conn or not serial_conn.is_open:
        return set()

    # Checking for connected servos
    print(f"Scanning for servos...")
    discovered_servos = set()
    
    # Only try SCS protocol format as it was used in previous implementation
    for id in range(1, 16):  # Limit to likely servo IDs (1-15)
        try:
            # SCS protocol format for ping (based on previous implementation)
            cmd = bytearray([0xFF, 0xFF, id, 2, 1])
            checksum = (~sum(cmd[2:]) & 0xFF)
            cmd.append(checksum)
            
            # Send quietly without logging every attempt
            serial_conn.write(cmd)
            serial_conn.flush()
            time.sleep(0.05)  # Short wait for response
            response = serial_conn.read(serial_conn.in_waiting)
            
            # Check response
            if response and len(response) > 0:
                discovered_servos.add(id)
        except Exception as e:
            print(f"Error while pinging servo {id}: {e}")

    # Only print results at the end
    if discovered_servos:
        print(f"Found servos with IDs: {discovered_servos}")
    else:
        print("No servos found")
        
    return discovered_servos