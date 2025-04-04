#!/usr/bin/env python3
"""Script to flash Tracks firmware to a Raspberry Pi Pico device.

Usage:
    python3 flash_firmware.py /dev/serial/by-id/usb-Raspberry_Pi_Pico_E66...-if00

This script uses picotool to find the running Pico via its serial port,
reboot it into BOOTSEL mode, and then load the UF2 firmware file.

Requires 'picotool' and 'udevadm' in the system PATH.
May require appropriate permissions (udev rules or sudo) for picotool
to interact with USB devices.

Firmware location: "firmware/build/tracks_firmware.uf2" relative to parent dir.
"""

import sys
import subprocess
import os
import time

def find_usb_details(device_path: str) -> tuple[Optional[str], Optional[str]]:
    """Use udevadm to find the USB bus and device number for a serial device path.

    Args:
        device_path: The path to the serial device (e.g., /dev/ttyACM0).

    Returns:
        A tuple containing (bus_number, device_number) as strings, or (None, None)
        if they cannot be determined.
    """
    busnum = None
    devnum = None
    try:
        # Command to get the device path in the sysfs
        cmd_path = f"udevadm info -q path -n {device_path}"
        path_result = subprocess.run(cmd_path, shell=True, capture_output=True, text=True, check=True)
        sysfs_path = path_result.stdout.strip()

        # Command to get attributes up to the USB device level
        cmd_info = f"udevadm info -a -p {sysfs_path}"
        info_result = subprocess.run(cmd_info, shell=True, capture_output=True, text=True, check=True)

        # Go line by line upwards until we find the USB device attributes
        for line in info_result.stdout.splitlines():
            line = line.strip()
            if 'ATTRS{busnum}' in line:
                try:
                    busnum = line.split('==')[1].strip().strip('"')
                except IndexError:
                    pass # Ignore malformed lines
            elif 'ATTRS{devnum}' in line:
                try:
                    devnum = line.split('==')[1].strip().strip('"')
                except IndexError:
                    pass # Ignore malformed lines
            # Stop once we have both, assuming they belong to the same device entry
            if busnum and devnum:
                break

    except subprocess.CalledProcessError as e:
        print(f"Error running udevadm command: {e.stderr}")
        # Don't exit here, maybe picotool can still find it
    except FileNotFoundError:
        print("Error: 'udevadm' command not found. Cannot determine bus/device.")
        # Don't exit here, maybe picotool can still find it
    except Exception as e:
        print(f"Unexpected error getting device details: {e}")

    return busnum, devnum


def flash_firmware(device_path: str) -> None:
    """Flash the compiled firmware UF2 file to the specified Pico device.

    Locates the firmware file, attempts to find the USB bus/device number
    of the running Pico using the serial path, reboots the Pico into BOOTSEL
    mode using `picotool`, waits, and then loads the firmware using `picotool`.

    Args:
        device_path: The serial device path of the Pico in run mode.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    firmware_file = os.path.join(script_dir, "..", "firmware", "build", "tracks_firmware.uf2")

    if not os.path.isfile(firmware_file):
        print(f"❌ Firmware file not found: {firmware_file}")
        sys.exit(1)

    print("-" * 60)
    print(f"Target Serial Device: {device_path}")
    print(f"Firmware File:      {firmware_file}")
    print("-" * 60)

    # 1. Find Bus/Device number of the RUNNING Pico (Serial Mode)
    busnum, devnum = find_usb_details(device_path)
    if busnum and devnum:
        print(f"ℹ️ Found running Pico at: Bus {busnum}, Device {devnum}")
    else:
        print("⚠️ Could not determine bus/device for running Pico via udevadm.")
        print("   Will proceed with auto-detect for reboot/load, may fail.")
        print("   Ensure correct permissions (udev rules / sudo).")

    # 2. Attempt to Reboot the specific Pico into BOOTSEL mode
    reboot_success = False
    if busnum and devnum: # Only try targeted reboot if we have bus/dev
        reboot_cmd = ["picotool", "reboot", "-b", "--bus", busnum, "--address", devnum]
        print(f"⚙️ Sending Reboot Command: {' '.join(reboot_cmd)}")
        try:
            # Use timeout, as device might disappear quickly
            result = subprocess.run(reboot_cmd, check=False, timeout=5, capture_output=True, text=True) # check=False initially
            if result.returncode == 0:
                 print("✅ Reboot command sent successfully.")
                 reboot_success = True
            elif "no device found" in result.stderr.lower() or "no RP2040 device found" in result.stderr.lower():
                 print("⚠️ Reboot command failed: Device not found (maybe already in BOOTSEL?). Continuing...")
                 # Assume it might already be in BOOTSEL or will be found by load
                 reboot_success = True # Treat as "ok to proceed"
            elif "permission" in result.stderr.lower() or result.returncode == 246: # 246 often permission related
                 print("❌ Reboot command failed: Permission denied.")
                 print("   Try running the make command with 'sudo' or set up udev rules for picotool.")
                 # sys.exit(result.returncode) # Exit if permissions clearly fail
                 print("   Continuing load attempt, but it may fail...")
            else:
                 print(f"⚠️ Reboot command returned error (code {result.returncode}):")
                 print(result.stderr.strip())
                 print("   Continuing load attempt...")


        except subprocess.TimeoutExpired:
             print("ℹ️ Reboot command timed out (Pico likely reset). Continuing...")
             reboot_success = True # Assume reset happened
        except FileNotFoundError:
            print("❌ Error: 'picotool' command not found in PATH.")
            sys.exit(1)
        except Exception as e:
             print(f"⚠️ Unexpected error during reboot attempt: {e}")
             print("   Continuing load attempt...")
    else:
        print("ℹ️ Skipping targeted reboot (no bus/device info). Relying on load auto-detect.")
        reboot_success = True # Allow load attempt

    # Give the OS time to recognize the mode change / device re-enumeration
    if reboot_success:
        print("⏳ Waiting briefly for device mode change...")
        time.sleep(3)

    # 3. Load the firmware, auto-detecting the BOOTSEL device
    load_cmd = ["picotool", "load", firmware_file, "-f"]
    print(f"⚙️ Sending Load Command: {' '.join(load_cmd)}")
    try:
        # Don't specify bus/address - let load find the BOOTSEL device
        result = subprocess.run(load_cmd, check=True, capture_output=True, text=True)
        print("✅ Firmware flashed successfully!")
        print(result.stdout.strip()) # Show picotool output

    except subprocess.CalledProcessError as e:
        print(f"❌ Error flashing firmware (code {e.returncode}):")
        print(e.stderr.strip())
        if "no device found" in e.stderr.lower() or "no RP2040 device found" in e.stderr.lower() :
             print("   Common causes: ")
             print("     - Pico not manually put into BOOTSEL mode.")
             print("     - Automatic reboot failed (permissions? udev rules?).")
             print("     - USB cable issue.")
        elif "permission" in e.stderr.lower():
             print("   Try running the make command with 'sudo' or set up udev rules for picotool.")
        sys.exit(e.returncode) # Exit with picotool's error code
    except FileNotFoundError:
        print("❌ Error: 'picotool' command not found in PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during load: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python3 {os.path.basename(__file__)} <device_path>")
        print(f"   Example: python3 {os.path.basename(__file__)} /dev/ttyACM0")
        sys.exit(1)

    # Basic check if device path looks like a serial device
    if not sys.argv[1].startswith('/dev/'):
        print(f"Warning: Device path '{sys.argv[1]}' doesn't look like a /dev path.")
        # Continue anyway, maybe it's valid in some context

    flash_firmware(sys.argv[1])
