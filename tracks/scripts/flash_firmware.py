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
        cmd = f"udevadm info -a -p $(udevadm info -q path -n {device_path})"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running udevadm: {e}")
        sys.exit(1)
    busnum = None
    devnum = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith('ATTRS{busnum}'):
            busnum = line.split('==')[1].strip().strip('"')
        elif line.startswith('ATTRS{devnum}'):
            devnum = line.split('==')[1].strip().strip('"')
        if busnum and devnum:
            break
    if busnum and devnum:
        print(f"Detected device: Bus {busnum}, Device {devnum}")
    else:
        print("Could not determine bus and device numbers from udev info.")
    try:
        subprocess.run(["picotool", "load", firmware_file, "-f", '--bus', busnum, '--address', devnum], check=True)
        print("Firmware flashed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error flashing firmware: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 flash_firmware.py <device_path>")
        sys.exit(1)
    flash_firmware(sys.argv[1])
