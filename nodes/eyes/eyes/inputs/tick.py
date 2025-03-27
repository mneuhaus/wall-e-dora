"""Tick input handler for the eyes node."""
import os
import time
import socket
import subprocess
import platform
import requests
import hashlib
from pathlib import Path
import glob


class GifSyncHandler:
    """Simple handler for syncing GIF images to eye displays."""
    
    def __init__(self):
        self.last_sync_time = 0
        self.sync_interval = 60  # seconds
        # Correctly locate the gif_sync directory relative to the eyes package
        self.current_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.gif_sync_dir = self.current_dir / "gif_sync"
        
        print(f"GIF sync directory: {self.gif_sync_dir}")
        if not self.gif_sync_dir.exists():
            print(f"Warning: GIF sync directory not found at {self.gif_sync_dir}")
    
    def should_sync(self):
        """Check if it's time to perform a sync."""
        current_time = time.time()
        if current_time - self.last_sync_time >= self.sync_interval:
            return True
        return False
    
    def find_devices(self):
        """Find Wall-E eye displays using fixed IP addresses."""
        print("Looking for eye displays at fixed IP addresses...")
        devices = []
        
        # Use fixed IPs instead of scanning
        fixed_ips = [
            "10.42.0.156",
            "10.42.0.218"
        ]
        
        for ip in fixed_ips:
            if self._check_device(ip):
                print(f"Found eye display at {ip}")
                devices.append(ip)
            else:
                print(f"Eye display not reachable at {ip}")
        
        return devices
    
    def _is_valid_ip(self, ip):
        """Check if a string is a valid IP address."""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    def _check_device(self, ip):
        """Check if an IP address belongs to an eye display."""
        print(f"Checking if {ip} is an eye display...")
        try:
            # Much longer timeout for ESP32 devices
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(20.0)  # Increased to 20 seconds for ESP32 devices
            result = sock.connect_ex((ip, 80))
            sock.close()
            
            if result != 0:
                print(f"Port 80 not open on {ip} (code: {result})")
                return False
            
            print(f"Port 80 open on {ip}, checking if it's an eye display...")
                
            # Now check if it's our device by requesting the gifs endpoint
            # Much longer timeout for ESP32 devices
            try:
                print(f"Requesting /gifs from {ip} (timeout: 20s)...")
                response = requests.get(f"http://{ip}/gifs", timeout=20.0)  # Increased to 20 seconds
                if response.status_code != 200:
                    print(f"Got HTTP status {response.status_code} from {ip}/gifs")
                    return False
                
                print(f"Checking JSON response from {ip}...")
                files = response.json()  # Will raise exception if not JSON
                print(f"Found {len(files)} files on device at {ip}")
                return True
                
            except requests.exceptions.RequestException as e:
                print(f"HTTP request error for {ip}: {e}")
                return False
            except ValueError as e:
                print(f"JSON parsing error for {ip}: {e}")
                return False
                
        except Exception as e:
            print(f"Connection error for {ip}: {e}")
            return False
    
    def sync_files(self, ip):
        """Sync GIF files to the device."""
        if not self.gif_sync_dir.exists():
            print(f"GIF sync directory not found: {self.gif_sync_dir}")
            return False
        
        try:
            # Get list of files on device
            device_files = self._get_device_files(ip)
            print(f"Found {len(device_files)} files on device")
            
            # Get list of local files
            local_files = self._get_local_files()
            print(f"Found {len(local_files)} local files")
            
            # Determine which files to upload
            to_upload = self._determine_files_to_upload(local_files, device_files)
            print(f"Need to upload {len(to_upload)} files")
            
            # Upload files
            success_count = 0
            for file_path in to_upload:
                if self._upload_file(ip, file_path):
                    success_count += 1
            
            print(f"Uploaded {success_count} of {len(to_upload)} files successfully")
            return success_count == len(to_upload)
        except Exception as e:
            print(f"Error syncing files: {e}")
            return False
    
    def _get_device_files(self, ip):
        """Get list of files on the device."""
        try:
            # Try to use the enhanced endpoint that would return checksums
            try:
                print(f"Checking for enhanced files API on {ip}...")
                response = requests.get(f"http://{ip}/files", timeout=20.0)
                if response.status_code == 200:
                    try:
                        print(f"Parsing response from enhanced API...")
                        # If we have enhanced API with checksums
                        return response.json()
                    except Exception as e:
                        print(f"Failed to parse JSON from enhanced API: {e}")
                        pass
            except Exception as e:
                print(f"Enhanced API not available: {e}")
                pass
            
            # Fall back to the simple API
            print(f"Requesting file list from {ip} via basic API...")
            response = requests.get(f"http://{ip}/gifs", timeout=20.0)
            if response.status_code == 200:
                print(f"Parsing file list from {ip}...")
                filenames = response.json()
                print(f"Found {len(filenames)} files on device at {ip}")
                # Return all filenames with null metadata
                return {filename: {'checksum': None, 'size': None} for filename in filenames}
            else:
                print(f"Error retrieving file list: HTTP {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error getting files from device: {e}")
            return {}
    
    def _get_local_files(self):
        """Get dictionary of local files with their checksums."""
        local_files = {}
        
        # Get all gif and jpg files in the local directory
        for ext in ['*.gif', '*.jpg', '*.jpeg', '*.GIF', '*.JPG', '*.JPEG']:
            for file_path in glob.glob(os.path.join(self.gif_sync_dir, ext)):
                filename = os.path.basename(file_path)
                try:
                    checksum = self._calculate_file_md5(file_path)
                    file_size = os.path.getsize(file_path)
                    local_files[filename] = {
                        'path': file_path,
                        'checksum': checksum,
                        'size': file_size
                    }
                except Exception as e:
                    print(f"Error calculating checksum for {filename}: {e}")
        
        return local_files
    
    def _calculate_file_md5(self, file_path):
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _determine_files_to_upload(self, local_files, device_files):
        """Determine which files need to be uploaded."""
        to_upload = []
        
        # Files to upload (if not on device or different checksum)
        for filename, local_info in local_files.items():
            if filename not in device_files:
                to_upload.append(local_info['path'])
            elif device_files[filename]['checksum'] is not None and local_info['checksum'] != device_files[filename]['checksum']:
                to_upload.append(local_info['path'])
        
        return to_upload
    
    def _upload_file(self, ip, file_path):
        """Upload a single file to the device."""
        filename = os.path.basename(file_path)
        
        try:
            # Get file size for logging
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"Uploading {filename} ({file_size:.1f} KB) to {ip}...")
            
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                # Longer timeout for file uploads - ESP32 devices are slow at processing uploads
                # 60 seconds timeout for file uploads (ESP32 devices are very slow)
                print(f"Starting upload with 60s timeout...")
                response = requests.post(f'http://{ip}/upload', files=files, timeout=60.0)
                
                # Accept both 302 (redirect) and 200 (OK) as success
                if response.status_code in [200, 302]:
                    print(f"Successfully uploaded {filename} to {ip}")
                    return True
                else:
                    print(f"Failed to upload {filename}: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"Error uploading {filename}: {e}")
            return False
    
    def perform_sync(self):
        """Run the sync process."""
        self.last_sync_time = time.time()
        
        # Find devices
        devices = self.find_devices()
        if not devices:
            print("No eye displays found on the network")
            return False
        
        # Sync files to each device
        success = True
        for ip in devices:
            print(f"Syncing files to {ip}...")
            if not self.sync_files(ip):
                success = False
        
        return success


# Global instance for tick handler
_gif_sync_handler = GifSyncHandler()


def process_tick(context, event):
    """
    Process a tick event for synchronizing GIF images to reachable eyes.
    
    Args:
        context (dict): The context dictionary containing dependencies.
        event (dict): The event data.
        
    Returns:
        None
    """
    global _gif_sync_handler
    
    if _gif_sync_handler.should_sync():
        print("Starting GIF synchronization...")
        success = _gif_sync_handler.perform_sync()
        if success:
            print("GIF sync completed successfully")
        else:
            print("GIF sync completed with some errors")
    
    return None