"""Input handler for playing GIFs on eye displays."""
import requests
import pyarrow as pa
import logging
import concurrent.futures
from functools import partial


def process_play_gif(context, event):
    """
    Process a play_gif event to display a GIF on the eye displays.
    
    Args:
        context (dict): The context dictionary containing dependencies.
        event (dict): The event data containing the filename of the GIF to play.
        
    Returns:
        None
    """
    # Extract filename from event data
    try:
        print(f"Received play_gif event: {event}")
        
        if not event.get("value"):
            print("Error: No value in play_gif event")
            return None
            
        # Check the type of the value
        if hasattr(event["value"], 'to_pylist'):
            # If it's an Arrow array
            data = event["value"].to_pylist()
            print(f"Parsed data from Arrow array: {data}")
        else:
            # Assume it's already a list or other iterable
            data = event["value"]
            print(f"Using data directly: {data}")
            
        if not data or len(data) == 0:
            print("Error: Empty data in play_gif event")
            return None
            
        filename = data[0]
        print(f"Received play_gif event for file: {filename}")
        
        # Use fixed IPs for eye displays
        eye_displays = [
            "10.42.0.156",
            "10.42.0.218"
        ]
        
        # Send requests to both eye displays in parallel
        print(f"Sending parallel requests to {len(eye_displays)} eye displays")
        results = send_parallel_requests(eye_displays, filename)
        
        # Count successful requests
        success_count = sum(1 for success in results if success)
        
        if success_count == len(eye_displays):
            print(f"Successfully sent {filename} to all eye displays")
        elif success_count > 0:
            print(f"Sent {filename} to {success_count}/{len(eye_displays)} eye displays")
        else:
            print(f"Failed to send {filename} to any eye displays")
    
    except Exception as e:
        print(f"Error processing play_gif event: {e}")
    
    return None


def send_parallel_requests(ips, filename):
    """
    Send parallel requests to multiple eye displays.
    
    Args:
        ips (list): List of IP addresses of the eye displays.
        filename (str): Name of the GIF file to play.
        
    Returns:
        list: List of boolean results, True for successful requests.
    """
    # Create a function with the filename parameter already set
    request_fn = partial(send_play_request, filename=filename)
    
    # Use a thread pool to execute requests in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ips)) as executor:
        # Map the function to each IP address
        results = list(executor.map(request_fn, ips))
    
    return results


def send_play_request(ip, filename):
    """
    Send a request to play a GIF on an eye display.
    
    Args:
        ip (str): IP address of the eye display.
        filename (str): Name of the GIF file to play.
        
    Returns:
        bool: True if request was successful, False otherwise.
    """
    try:
        # Format URL for the eye display's playgif endpoint
        url = f"http://{ip}/playgif?name={filename}"
        print(f"Sending request to {url}")
        
        # Use a long timeout for ESP32 devices (20 seconds)
        response = requests.get(url, timeout=20.0)
        
        if response.status_code == 200:
            print(f"Successfully sent play request to {ip}")
            return True
        else:
            print(f"Failed to send play request to {ip}: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request error for {ip}: {e}")
        return False
    except Exception as e:
        print(f"Error sending play request to {ip}: {e}")
        return False