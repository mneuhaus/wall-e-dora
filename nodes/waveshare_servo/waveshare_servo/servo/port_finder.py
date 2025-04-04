"""Utility function to find the serial port for the Waveshare servo controller."""

import os
from typing import Optional

import serial.tools.list_ports


def find_servo_port() -> Optional[str]:
    """Find the serial port connected to the Waveshare servo controller.

    Attempts to find the port first by a specific device ID path (if it exists)
    and then falls back to scanning all available serial ports for common
    USB-to-Serial chip identifiers.

    Returns:
        The device path string (e.g., '/dev/ttyUSB0') if found, otherwise None.
    """
    # Try by direct name first (this was used in the previous implementation)
    try:
        device_path = '/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FD016638-if00'
        if os.path.exists(device_path):
            print(f"Found servo controller at {device_path}")
            return device_path
    except Exception as e:
        print(f"Error checking direct device path: {e}")
    
    # Fall back to scanning ports
    try:
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            # Check for typical USB-Serial device identifiers
            if any(id_str in port.description for id_str in 
                  ["USB-Serial", "CP210", "CH340", "FTDI"]):
                print(f"Found servo controller at {port.device}")
                return port.device
    except Exception as e:
        print(f"Error scanning serial ports: {e}")
        
    print("No servo controller found by name or USB identifiers")
    return None
