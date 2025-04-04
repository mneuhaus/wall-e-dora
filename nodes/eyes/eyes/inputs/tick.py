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
        self.sync_interval = 300  # seconds (5 minutes)
        # Correctly locate the gif_sync directory relative to the eyes package
        self.current_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.gif_sync_dir = self.current_dir / "gif_sync"
    
    def should_sync(self):
        """Check if it's time to perform a sync."""
        current_time = time.time()
        if current_time - self.last_sync_time >= self.sync_interval:
            return True
        return False
    
    def find_devices(self):
        """Find Wall-E eye displays using fixed IP addresses."""
        devices = []
        
        # Use fixed IPs instead of scanning
        fixed_ips = [
            "10.42.0.156",
            "10.42.0.218"
        ]
        
        for ip in fixed_ips:
            if self._check_device(ip):
                devices.append(ip)
        
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
        try:
            # Much longer timeout for ESP32 devices
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(20.0)  # Increased to 20 seconds for ESP32 devices
            result = sock.connect_ex((ip, 80))
            sock.close()
            
            if result != 0:
                return False
                
            # Now check if it's our device by requesting the gifs endpoint
            # Much longer timeout for ESP32 devices
            try:
                response = requests.get(f"http://{ip}/gifs", timeout=20.0)  # Increased to 20 seconds
                if response.status_code != 200:
                    return False
                
                files = response.json()  # Will raise exception if not JSON
                print(f"Found {len(files)} files on device at {ip}")
                return True
                
            except (requests.exceptions.RequestException, ValueError):
                return False
                
        except Exception:
            return False
    
    def sync_files(self, ip):
        """Sync GIF files to the device."""
        if not self.gif_sync_dir.exists():
            return False
        
        try:
            # Get list of files on device
            device_files = self._get_device_files(ip)
            
            # Get list of local files
            local_files = self._get_local_files()
            
            # Determine which files to upload
            to_upload = self._determine_files_to_upload(local_files, device_files)
            
            # Upload files
            success_count = 0
            for file_path in to_upload:
                if self._upload_file(ip, file_path):
                    success_count += 1
            
            return success_count == len(to_upload)
        except Exception:
            return False
    
    def _get_device_files(self, ip):
        """Get list of files on the device."""
        try:
            # Try to use the enhanced endpoint that would return checksums
            try:
                response = requests.get(f"http://{ip}/files", timeout=20.0)
                if response.status_code == 200:
                    try:
                        # If we have enhanced API with checksums
                        return response.json()
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Fall back to the simple API
            response = requests.get(f"http://{ip}/gifs", timeout=20.0)
            if response.status_code == 200:
                filenames = response.json()
                # Return all filenames with null metadata
                return {filename: {'checksum': None, 'size': None} for filename in filenames}
            else:
                return {}
        except Exception:
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
                except Exception:
                    pass
        
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
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                # 60 seconds timeout for file uploads (ESP32 devices are very slow)
                response = requests.post(f'http://{ip}/upload', files=files, timeout=60.0)
                
                # Accept both 302 (redirect) and 200 (OK) as success
                return response.status_code in [200, 302]
        except Exception:
            return False
    
    def perform_sync(self):
        """Run the sync process."""
        self.last_sync_time = time.time()
        
        # Find devices
        devices = self.find_devices()
        if not devices:
            return False
        
        # Sync files to each device
        success = True
        for ip in devices:
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
        _gif_sync_handler.perform_sync()
    
    return None