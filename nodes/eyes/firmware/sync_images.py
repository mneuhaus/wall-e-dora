#!/usr/bin/env python3
"""Script to synchronize image files between a local directory and Wall-E eye devices.

Scans the network for devices (or uses a specified IP), compares local files
(GIFs/JPGs) with files on the device using MD5 checksums (if available on the device),
and uploads/deletes files as needed to keep them in sync.

Requires 'requests' and 'tqdm' Python packages.
Network scanning relies on standard OS tools ('ping', 'netstat', 'ipconfig').
"""

import os
import sys
import time
import socket
import argparse
import requests
import hashlib
from pathlib import Path
import socket
import subprocess
import platform
import glob
import concurrent.futures
from tqdm import tqdm


def find_devices() -> list[str]:
    """Scan the network for Wall-E eye devices.

    Attempts to find devices using mDNS first (if available on the OS).
    If mDNS fails or is unavailable, falls back to scanning common local
    network IP ranges (192.168.0.x, 192.168.1.x, 10.0.0.x, etc.).

    Returns:
        A list of IP addresses of discovered Wall-E eye devices.
    """
    print("Scanning for Wall-E eye devices...")
    # Try to find devices using mDNS for better user experience if available
    if platform.system() == "Darwin" or platform.system() == "Linux":
        try:
            # Try to use mDNS to find the device with hostname wall-e.neuhaus.nrw
            result = subprocess.run(
                ["ping", "-c", "1", "wall-e.neuhaus.nrw"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=3
            )
            
            if result.returncode == 0:
                # Extract IP from ping output
                output = result.stdout.decode()
                for line in output.split('\n'):
                    if "PING" in line:
                        parts = line.split()
                        for part in parts:
                            if "(" in part and ")" in part:
                                ip = part.strip("()")
                                if is_valid_ip(ip):
                                    print(f"Found device via mDNS: {ip}")
                                    return [ip]
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass  # mDNS failed, fall back to scanning
    
    # Fall back to IP scanning in common local network ranges
    found_devices = []
    potential_gateways = get_potential_gateways()
    
    # Create a list of all IPs to scan
    ips_to_scan = []
    for base_ip in potential_gateways:
        for i in range(1, 255):
            ips_to_scan.append(f"{base_ip}.{i}")
    
    # Use parallel execution to scan IPs
    print(f"Scanning {len(ips_to_scan)} potential IP addresses in parallel...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_ip = {executor.submit(check_device, ip): ip for ip in ips_to_scan}
        
        # Use tqdm for a progress bar
        with tqdm(total=len(ips_to_scan)) as pbar:
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    is_device = future.result()
                    if is_device:
                        print(f"\nFound Wall-E eye device at {ip}")
                        found_devices.append(ip)
                except Exception as exc:
                    pass
                finally:
                    pbar.update(1)
    
    return found_devices


def get_potential_gateways() -> list[str]:
    """Attempt to determine potential network gateway base IPs.

    Uses OS-specific commands ('ipconfig', 'netstat') to find the default
    gateway and extracts the first three octets (e.g., "192.168.1").
    Falls back to common home network ranges if detection fails.

    Returns:
        A list of potential base IP address strings (e.g., ["192.168.1", "10.0.0"]).
    """
    gateways = []
    # Common home network ranges
    common_ranges = ["192.168.0", "192.168.1", "192.168.2", "10.0.0", "10.0.1", "10.42.0"]
    
    # Try to get the actual gateway first
    if platform.system() == "Windows":
        try:
            output = subprocess.check_output("ipconfig", text=True)
            for line in output.split('\n'):
                if "Default Gateway" in line and "." in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        ip = parts[1].strip()
                        if is_valid_ip(ip):
                            subnet = ".".join(ip.split(".")[0:3])
                            gateways.append(subnet)
        except subprocess.SubprocessError:
            pass
    elif platform.system() in ["Darwin", "Linux"]:
        try:
            output = subprocess.check_output("netstat -rn | grep default", shell=True, text=True)
            for line in output.split('\n'):
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[1]
                    if is_valid_ip(ip):
                        subnet = ".".join(ip.split(".")[0:3])
                        gateways.append(subnet)
        except subprocess.SubprocessError:
            pass
    
    # Add common ranges if we didn't find anything
    if not gateways:
        gateways = common_ranges
    
    return gateways


def is_valid_ip(ip: str) -> bool:
    """Check if the string is a valid IPv4 address.

    Args:
        ip: The string to validate.

    Returns:
        True if the string is a valid IPv4 address, False otherwise.
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def check_device(ip: str) -> bool:
    """Check if the device at the given IP address is a Wall-E eye display.

    Performs a quick socket connection check on port 80, followed by an HTTP
    GET request to the '/gifs' endpoint to confirm it's the target device.

    Args:
        ip: The IP address string to check.

    Returns:
        True if the device is identified as a Wall-E eye, False otherwise.
    """
    try:
        # Try to connect to port 80 first to quickly filter
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)  # Short timeout to speed up scanning
        result = sock.connect_ex((ip, 80))
        sock.close()
        
        if result != 0:
            return False
            
        # Now check if it's actually our device by requesting the gifs endpoint
        response = requests.get(f"http://{ip}/gifs", timeout=0.5)
        # If we get a JSON response, it's likely our device
        response.json()  # This will raise an exception if not JSON
        return True
    except Exception:
        return False


def calculate_file_md5(file_path: str) -> str:
    """Calculate the MD5 hash of a file.

    Args:
        file_path: The path to the file.

    Returns:
        The hexadecimal MD5 hash string.
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_local_files_with_checksums(local_dir: str) -> dict:
    """Get a dictionary of local image files with their metadata.

    Scans the specified directory for GIF and JPG/JPEG files, calculates
    their MD5 checksums and sizes.

    Args:
        local_dir: The path to the local directory to scan.

    Returns:
        A dictionary where keys are filenames and values are dictionaries
        containing 'path', 'checksum', and 'size'.
    """
    local_files = {}
    # Get all gif and jpg files in the local directory
    for ext in ['*.gif', '*.jpg', '*.jpeg', '*.GIF', '*.JPG', '*.JPEG']:
        for file_path in glob.glob(os.path.join(local_dir, ext)):
            filename = os.path.basename(file_path)
            try:
                checksum = calculate_file_md5(file_path)
                file_size = os.path.getsize(file_path)
                local_files[filename] = {
                    'path': file_path,
                    'checksum': checksum,
                    'size': file_size
                }
            except Exception as e:
                print(f"Error calculating checksum for {filename}: {str(e)}")
    
    return local_files


def get_device_files_with_metadata(ip: str, max_retries: int = 3) -> dict:
    """Get a dictionary of files on the device with metadata (checksum, size).

    Attempts to use an enhanced '/files' endpoint first (which should return
    checksums). If that fails or is unavailable, falls back to the basic
    '/gifs' endpoint which only returns filenames. Includes retry logic with
    increasing timeouts for robustness.

    Args:
        ip: The IP address of the device.
        max_retries: The maximum number of times to retry fetching data.

    Returns:
        A dictionary where keys are filenames and values are dictionaries
        containing 'checksum' and 'size' (which may be None if using fallback).
        Returns an empty dictionary on failure.
    """

    # Function for retrying with backoff
    def try_get_with_retry(url, max_retries=3, initial_timeout=2):
        for retry in range(max_retries):
            try:
                # Increase timeout with each retry
                timeout = initial_timeout * (retry + 1)
                print(f"Connecting to {url} (attempt {retry+1}/{max_retries}, timeout={timeout}s)")
                response = requests.get(url, timeout=timeout)
                return response
            except (requests.ConnectionError, requests.Timeout) as e:
                if retry < max_retries - 1:
                    wait_time = 1 * (retry + 1)
                    print(f"Connection error, retrying in {wait_time} seconds... ({str(e)})")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to connect after {max_retries} attempts: {str(e)}")
                    raise
    
    try:
        # First try to use the enhanced endpoint that would return checksums
        try:
            response = try_get_with_retry(f"http://{ip}/files", max_retries, 2)
            if response and response.status_code == 200:
                try:
                    # If we have enhanced API with checksums
                    return response.json()
                except:
                    pass
        except Exception as e:
            print(f"Enhanced API not available: {str(e)}")
            pass
        
        # Fall back to the simple API that just returns filenames
        try:
            response = try_get_with_retry(f"http://{ip}/gifs", max_retries, 2)
            if response and response.status_code == 200:
                filenames = response.json()
                print(f"Retrieved {len(filenames)} files from device API")
                # API now returns files from the /gif directory as expected
                # Return all filenames as a dictionary with null metadata
                return {filename: {'checksum': None, 'size': None} for filename in filenames}
            else:
                print(f"API returned status code: {response.status_code if response else 'None'}")
                return {}
        except Exception as e:
            print(f"Basic API error: {str(e)}")
            return {}
    except Exception as e:
        print(f"Error getting files from device: {str(e)}")
        return {}


def determine_sync_actions(local_files: dict, device_files: dict, delete_remote: bool = False) -> tuple[list, list]:
    """Determine which files need to be uploaded or deleted.

    Compares local files and device files based on existence and checksums (if available).

    Args:
        local_files: Dictionary of local files and their metadata.
        device_files: Dictionary of device files and their metadata.
        delete_remote: If True, identify files on the device that are not present locally.

    Returns:
        A tuple containing two lists: (files_to_upload, files_to_delete).
        'files_to_upload' contains local file paths.
        'files_to_delete' contains remote filenames.
    """
    to_upload = []
    to_delete = []
    
    # Files to upload (if not on device or different checksum)
    for filename, local_info in local_files.items():
        if filename not in device_files:
            to_upload.append(local_info['path'])
        elif device_files[filename]['checksum'] is not None and local_info['checksum'] != device_files[filename]['checksum']:
            to_upload.append(local_info['path'])
    
    # Files to delete from device (if not in local directory)
    if delete_remote:
        for filename in device_files:
            if filename not in local_files:
                to_delete.append(filename)
    
    return to_upload, to_delete


def upload_file(args: tuple) -> tuple[bool, str, str]:
    """Upload a single file to the device. Designed for parallel execution.

    Args:
        args: A tuple containing (ip_address, local_file_path).

    Returns:
        A tuple containing (success_boolean, filename, message).
    """
    ip, file_path = args
    filename = os.path.basename(file_path)
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(f'http://{ip}/upload', files=files, allow_redirects=False)
            
            # Accept both 302 (redirect) and 200 (OK) as success
            if response.status_code in [200, 302]:
                # Double-check the file was actually uploaded
                try:
                    # First try to get updated file list
                    check_response = requests.get(f"http://{ip}/gifs", timeout=2)
                    filenames = check_response.json()
                    if filename in filenames:
                        return (True, filename, "Success")
                    else:
                        # Try direct access as backup
                        direct_check = requests.head(f"http://{ip}/gif/{filename}", timeout=2)
                        if direct_check.status_code == 200:
                            return (True, filename, "Success (verified by direct access)")
                        else:
                            # File not found despite 200/302 response
                            return (False, filename, f"Upload appeared to succeed but file not found on device")
                except Exception as e:
                    # If we can't verify, assume success based on the upload response
                    return (True, filename, "Success (unverified)")
            else:
                return (False, filename, f"Failed: {response.status_code}")
    except Exception as e:
        return (False, filename, f"Error: {str(e)}")


def delete_file(args: tuple) -> tuple[bool, str, str]:
    """Delete a single file from the device. Designed for parallel execution.

    Args:
        args: A tuple containing (ip_address, filename_to_delete).

    Returns:
        A tuple containing (success_boolean, filename, message).
    """
    ip, filename = args
    try:
        response = requests.get(f'http://{ip}/delete?name={filename}', timeout=5)
        
        if response.status_code == 200:
            return (True, filename, "Deleted successfully")
        else:
            return (False, filename, f"Failed to delete: {response.status_code}")
    except Exception as e:
        return (False, filename, f"Error deleting: {str(e)}")


def sync_files(ip: str, files_to_upload: list, files_to_delete: list, max_workers: int = 5, use_parallel: bool = False) -> tuple[int, int]:
    """Perform file synchronization (uploads and deletes) with the device.

    Can operate sequentially (default) or in parallel (using ThreadPoolExecutor).
    Sequential mode is generally recommended for ESP32 stability.

    Args:
        ip: The IP address of the target device.
        files_to_upload: A list of local file paths to upload.
        files_to_delete: A list of filenames to delete from the device.
        max_workers: The number of parallel workers for uploads/deletes if use_parallel is True.
        use_parallel: If True, perform uploads and deletes in parallel threads.

    Returns:
        A tuple containing (number_of_successes, number_of_failures).
    """
    successes = 0
    failures = 0
    
    # Upload files
    if files_to_upload:
        print(f"Uploading {len(files_to_upload)} files to {ip}...")
        upload_args = [(ip, file_path) for file_path in files_to_upload]
        
        if not use_parallel:
            # Upload files one by one (default)
            with tqdm(total=len(files_to_upload), desc="Uploading files") as pbar:
                for arg in upload_args:
                    try:
                        success, filename, message = upload_file(arg)
                        if success:
                            print(f"✓ {filename}: {message}")
                            successes += 1
                        else:
                            print(f"✗ {filename}: {message}")
                            failures += 1
                    except Exception as exc:
                        print(f"✗ {os.path.basename(arg[1])}: Exception: {exc}")
                        failures += 1
                    finally:
                        pbar.update(1)
                    # Add a small delay between uploads to not overwhelm the device
                    time.sleep(0.5)
        else:
            # Use parallel execution for uploads (advanced option)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(upload_file, arg): arg[1] for arg in upload_args}
                
                with tqdm(total=len(files_to_upload), desc="Uploading files") as pbar:
                    for future in concurrent.futures.as_completed(future_to_file):
                        file_path = future_to_file[future]
                        filename = os.path.basename(file_path)
                        try:
                            success, filename, message = future.result()
                            if success:
                                print(f"✓ {filename}: {message}")
                                successes += 1
                            else:
                                print(f"✗ {filename}: {message}")
                                failures += 1
                        except Exception as exc:
                            print(f"✗ {filename}: Exception: {exc}")
                            failures += 1
                        finally:
                            pbar.update(1)
    
    # Delete files
    if files_to_delete:
        print(f"Deleting {len(files_to_delete)} files from {ip}...")
        delete_args = [(ip, filename) for filename in files_to_delete]
        
        if not use_parallel:
            # Delete files one by one (default)
            with tqdm(total=len(files_to_delete), desc="Deleting files") as pbar:
                for arg in delete_args:
                    try:
                        success, filename, message = delete_file(arg)
                        if success:
                            print(f"✓ Deleted {filename}")
                            successes += 1
                        else:
                            print(f"✗ Failed to delete {filename}: {message}")
                            failures += 1
                    except Exception as exc:
                        print(f"✗ Exception deleting {arg[1]}: {exc}")
                        failures += 1
                    finally:
                        pbar.update(1)
                    # Add a small delay between deletes
                    time.sleep(0.2)
        else:
            # Use parallel execution for deletes (advanced option)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(delete_file, arg): arg[1] for arg in delete_args}
                
                with tqdm(total=len(files_to_delete), desc="Deleting files") as pbar:
                    for future in concurrent.futures.as_completed(future_to_file):
                        filename = future_to_file[future]
                        try:
                            success, filename, message = future.result()
                            if success:
                                print(f"✓ Deleted {filename}")
                                successes += 1
                            else:
                                print(f"✗ Failed to delete {filename}: {message}")
                                failures += 1
                        except Exception as exc:
                            print(f"✗ Exception deleting {filename}: {exc}")
                            failures += 1
                        finally:
                            pbar.update(1)
    
    return successes, failures


def main():
    """Main execution function for the command-line sync tool."""
    parser = argparse.ArgumentParser(description='Sync local directory to Wall-E eye device')
    parser.add_argument('local_dir', type=str, help='Local directory containing GIF/JPG files')
    parser.add_argument('--ip', type=str, help='IP address of the device (optional - will auto-discover if not provided)')
    parser.add_argument('--force', action='store_true', help='Force upload of all files even if they exist on the device')
    parser.add_argument('--workers', type=int, default=50, help='Number of parallel workers for scanning (default: 50)')
    parser.add_argument('--upload-workers', type=int, default=5, help='Number of parallel uploads/deletes (default: 5)')
    parser.add_argument('--parallel', action='store_true', help='Use parallel uploads instead of sequential (not recommended)')
    parser.add_argument('--delete-remote', action='store_true', help='Delete files on device that do not exist locally')
    args = parser.parse_args()
    
    # Validate local directory
    if not os.path.isdir(args.local_dir):
        print(f"Error: {args.local_dir} is not a directory")
        sys.exit(1)
    
    # Find device if IP not provided
    if not args.ip:
        devices = find_devices()
        if not devices:
            print("No Wall-E eye devices found. Please check your network connection or specify an IP address with --ip.")
            sys.exit(1)
        
        if len(devices) > 1:
            print("Multiple devices found:")
            for i, ip in enumerate(devices):
                print(f"{i+1}. {ip}")
            choice = input("Select a device (number): ")
            try:
                device_index = int(choice) - 1
                ip = devices[device_index]
            except (ValueError, IndexError):
                print("Invalid selection")
                sys.exit(1)
        else:
            ip = devices[0]
    else:
        ip = args.ip
    
    # Get local and device files with checksums
    print("Scanning local files...")
    local_files = get_local_files_with_checksums(args.local_dir)
    print(f"Found {len(local_files)} local files")
    
    print("Getting device files...")
    device_files = get_device_files_with_metadata(ip)
    print(f"Found {len(device_files)} files on device")
    
    # Determine which files to upload and delete
    if args.force:
        # Force upload all local files
        files_to_upload = [info['path'] for _, info in local_files.items()]
        files_to_delete = []
        if args.delete_remote:
            files_to_delete = [filename for filename in device_files if filename not in local_files]
    else:
        # Smart sync - only upload changed files
        files_to_upload, files_to_delete = determine_sync_actions(local_files, device_files, args.delete_remote)
    
    # Print summary before syncing
    if files_to_upload:
        print(f"Files to upload ({len(files_to_upload)}):")
        for file_path in files_to_upload[:5]:
            print(f"  {os.path.basename(file_path)}")
        if len(files_to_upload) > 5:
            print(f"  ... and {len(files_to_upload) - 5} more")
    else:
        print("No files to upload")
        
    if files_to_delete:
        print(f"Files to delete from device ({len(files_to_delete)}):")
        for filename in files_to_delete[:5]:
            print(f"  {filename}")
        if len(files_to_delete) > 5:
            print(f"  ... and {len(files_to_delete) - 5} more")
    else:
        print("No files to delete from device")
    
    # Confirm the operation if it's significant
    total_operations = len(files_to_upload) + len(files_to_delete)
    if total_operations > 10:
        confirm = input(f"About to perform {total_operations} operations. Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            sys.exit(0)
    
    # Sync files
    if files_to_upload or files_to_delete:
        # Warn if using parallel mode
        if args.parallel:
            print("WARNING: Using parallel uploads may overwhelm the device. Use with caution!")
            time.sleep(2)
        
        successes, failures = sync_files(
            ip, 
            files_to_upload, 
            files_to_delete, 
            max_workers=args.upload_workers, 
            use_parallel=args.parallel
        )
        print(f"Sync completed: {successes} successful operations, {failures} failures")
    else:
        print("Nothing to do - device is already in sync with local directory")

if __name__ == "__main__":
    main()
