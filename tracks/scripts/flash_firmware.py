#!/usr/bin/env python3
"""
Script to flash Tracks firmware to the device.

Usage:
    python3 flash_firmware.py /dev/serial/by-id/usb-Raspberry_Pi_Pico_E6632891E3959D25-if00

This script uses picotool to load the UF2 firmware file onto the device.
Ensure that the UF2 firmware file is located at "firmware/build/tracks_firmware.uf2".
"""

import sys
import subprocess
import os

def flash_firmware(device_path: str) -> None:
    firmware_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firmware", "build", "tracks_firmware.uf2")
    if not os.path.isfile(firmware_file):
        print(f"Firmware file not found: {firmware_file}")
        sys.exit(1)
    print(f"Flashing firmware from {firmware_file} to {device_path}...")
    try:
        subprocess.run(["picotool", "load", firmware_file, "-f"], check=True)
        print("Firmware flashed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error flashing firmware: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 flash_firmware.py <device_path>")
        sys.exit(1)
    flash_firmware(sys.argv[1])