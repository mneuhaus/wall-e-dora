import threading
import asyncio
import os
import math
import jinja2
from aiohttp import web
import aiohttp_debugtoolbar
import json
import logging
import pyarrow as pa
import subprocess
import time
import queue  # Import the queue module
import aiofiles # Import aiofiles for async file operations
import ssl # Import ssl

# Assuming these handlers exist in the specified location relative to this file
# If they are elsewhere, adjust the import path accordingly
script_dir = os.path.dirname(os.path.abspath(__file__))
handlers_dir = os.path.join(script_dir, 'handlers') # Assuming handlers is a subfolder
if handlers_dir not in os.sys.path:
     os.sys.path.insert(0, handlers_dir)

try:
    # Make sure dora is available in the environment
    from dora import Node
except ImportError:
    print("ERROR: Could not import 'dora'. Make sure it's installed and accessible.")
    # Depending on the use case, you might exit here or handle it differently
    # sys.exit(1)
    # For now, define a dummy Node for testing without dora
    class Node:
        def __init__(self):
            print("WARNING: Using dummy Dora Node class.")
        def __iter__(self):
            print("Dummy Node: Starting event iteration (will yield nothing).")
            # Yield a dummy tick event periodically for testing loops
            count = 0
            while count < 5: # Limit dummy ticks
                yield {"type": "INPUT", "id": "tick"}
                time.sleep(1)
                count += 1
            yield {"type": "STOP"} # Simulate stop after a while
        def send_output(self, output_id, data, metadata):
            print(f"Dummy Node: Sending output '{output_id}' (ignored)")

# Import handlers after adjusting path and defining Node
try:
    from gamepad_profiles import (
        GamepadProfileManager,
        handle_save_gamepad_profile,
        handle_get_gamepad_profile,
        handle_check_gamepad_profile,
        handle_delete_gamepad_profile,
        handle_list_gamepad_profiles,
        emit_profiles_list
    )
except ImportError as e:
    print(f"ERROR: Could not import gamepad profile handlers: {e}")
    # Define dummy handlers if needed for testing without them
    class GamepadProfileManager: pass
    def handle_save_gamepad_profile(*args): pass
    def handle_get_gamepad_profile(*args): pass
    def handle_check_gamepad_profile(*args): pass
    def handle_delete_gamepad_profile(*args): pass
    def handle_list_gamepad_profiles(*args): pass
    def emit_profiles_list(*args): pass


# --- Configuration ---
GRID_STATE_FILENAME = "grid_state.json"
GRID_STATE_SAVE_INTERVAL = 15 # Seconds between automatic saves if dirty
LOG_LEVEL = logging.INFO # Default log level raised to INFO
WEBSERVER_PORT_HTTPS = 8443
WEBSERVER_PORT_HTTP = 8080
# --- End Configuration ---

# Configure logging format
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__) # Use a specific logger for this module

# --- Global State (Thread Safety Considerations) ---
global_web_input_queue = queue.Queue()
ws_clients = set()
ws_clients_lock = threading.Lock()
web_loop = None

current_grid_state = {}
grid_state_dirty = False
last_grid_state_save_time = time.time()
# --- End Global State ---

def get_grid_state_path():
    """Gets the absolute path to the grid state file."""
    return os.path.join(os.path.dirname(__file__), "..", GRID_STATE_FILENAME)

def load_grid_state_from_file():
    """Loads the grid state from the JSON file into memory. Blocking."""
    global current_grid_state
    grid_state_path = get_grid_state_path()
    if os.path.exists(grid_state_path):
        try:
            with open(grid_state_path, "r", encoding="utf-8") as f:
                current_grid_state = json.load(f)
                logger.info(f"Loaded grid state from {grid_state_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {grid_state_path}: {e}. Using empty default.")
            current_grid_state = {}
        except Exception as e:
            logger.error(f"Error loading grid state from {grid_state_path}: {e}. Using empty default.")
            current_grid_state = {}
    else:
        logger.warning(f"Grid state file not found at {grid_state_path}. Starting with empty state.")
        current_grid_state = {}

def save_grid_state_to_file():
    """Saves the current in-memory grid state to the JSON file. Blocking."""
    global grid_state_dirty, last_grid_state_save_time
    if not grid_state_dirty: # Avoid saving if nothing changed
         return
    grid_state_path = get_grid_state_path()
    try:
        temp_path = grid_state_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(current_grid_state, f, indent=2)
        os.replace(temp_path, grid_state_path)
        grid_state_dirty = False
        last_grid_state_save_time = time.time()
        logger.info(f"Saved grid state to {grid_state_path}")
    except Exception as e:
        logger.error(f"Error saving grid state to {grid_state_path}: {e}")

async def broadcast_grid_state_to_ws():
    """Broadcasts the current grid state to all WebSocket clients."""
    global current_grid_state
    response = {
        "id": "grid_state",
        "value": current_grid_state,
        "type": "EVENT"
    }
    serialized = json.dumps(response, default=str).encode('utf-8')
    if web_loop:
        asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
    else:
         logger.warning("Web loop not available for broadcasting grid state.")


def flush_web_inputs(node, profile_manager):
    """Processes events received from the web thread via the queue."""
    global current_grid_state, grid_state_dirty

    processed_count = 0
    try:
        while True:
            try:
                web_event = global_web_input_queue.get_nowait()
                processed_count += 1

                output_id = web_event.get("output_id")
                event_data = web_event.get("data")
                metadata = web_event.get("metadata", {})

                logger.debug(f"Processing web event: {output_id}")

                if output_id == "save_grid_state":
                    if isinstance(event_data, dict):
                        current_grid_state = event_data
                        grid_state_dirty = True
                        logger.debug("In-memory grid state updated. Marked as dirty.")
                        asyncio.run_coroutine_threadsafe(broadcast_grid_state_to_ws(), web_loop)
                    else:
                        logger.warning(f"Received 'save_grid_state' with invalid data type: {type(event_data)}")

                elif output_id == "save_joystick_servo":
                    widget_id = event_data.get("id")
                    axis = event_data.get("axis")
                    servo_id = event_data.get("servoId")

                    if widget_id and axis in ['x', 'y']:
                        if widget_id in current_grid_state:
                            servo_prop = f"{axis}ServoId"
                            if current_grid_state[widget_id].get(servo_prop) != servo_id:
                                current_grid_state[widget_id][servo_prop] = servo_id
                                grid_state_dirty = True
                                logger.info(f"Joystick {widget_id} {axis}-axis assigned to servo {servo_id}. Grid marked dirty.")
                                asyncio.run_coroutine_threadsafe(broadcast_grid_state_to_ws(), web_loop)
                            else:
                                logger.debug(f"Joystick {widget_id} {axis}-axis already set to servo {servo_id}. No change.")
                        else:
                            logger.warning(f"Cannot update joystick {widget_id}: widget not found in current grid state")
                    else:
                         logger.warning(f"Invalid 'save_joystick_servo' data: {event_data}")

                elif output_id == "get_grid_state":
                    logger.debug("Processing 'get_grid_state' request")
                    asyncio.run_coroutine_threadsafe(broadcast_grid_state_to_ws(), web_loop)

                elif output_id:
                    try:
                        node.send_output(
                            output_id=output_id,
                            data=pa.array(event_data if isinstance(event_data, list) else [event_data]),
                            metadata=metadata
                        )
                    except Exception as e:
                        logger.error(f"Error sending output '{output_id}' to Dora node: {e}")

                else:
                     logger.warning(f"Received web event with no 'output_id': {web_event}")

            except queue.Empty:
                break
            except Exception as e:
                 logger.error(f"Error processing web event {web_event}: {e}", exc_info=True)

    finally:
        if processed_count > 0:
            logger.debug(f"Processed {processed_count} web events from queue")

async def websocket_handler(request):
    """Handles WebSocket connections and messages."""
    global ws_clients, ws_clients_lock, global_web_input_queue

    logger.debug("New WebSocket connection request received")
    ws = web.WebSocketResponse()
    try:
        await ws.prepare(request)
    except Exception as e:
        logger.error(f"WebSocket prepare failed: {e}")
        return ws

    with ws_clients_lock:
        ws_clients.add(ws)
    logger.info(f"WebSocket client connected - {len(ws_clients)} active")

    try:
        welcome_msg = {
            "id": "connection_status",
            "value": {"status": "connected", "timestamp": time.time()},
            "type": "EVENT"
        }
        await ws.send_str(json.dumps(welcome_msg))
        logger.debug("Sent welcome message to client")

        initial_grid_state_msg = {
             "id": "grid_state",
             "value": current_grid_state,
             "type": "EVENT"
        }
        await ws.send_str(json.dumps(initial_grid_state_msg))
        logger.debug("Sent initial grid state to newly connected client.")

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    event = json.loads(msg.data)
                    output_id = event.get('output_id')
                    logger.debug(f"Received WS event, output_id: {output_id}")

                    if output_id in ['save_joystick_servo', 'save_grid_state', 'update_setting']:
                         log_data = str(event.get('data'))
                         if len(log_data) > 100: log_data = log_data[:100] + "..."
                         logger.debug(f"WS Event Details: ID={output_id}, Data={log_data}")

                    global_web_input_queue.put(event)

                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding WebSocket JSON message: {e}. Raw data: {msg.data[:200]}...")
                except Exception as e:
                    logger.error(f"Error processing WebSocket text message: {e}", exc_info=True)

            elif msg.type == web.WSMsgType.BINARY:
                logger.warning("Received unexpected binary WebSocket message, ignoring.")

            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"WebSocket connection closed with exception {ws.exception()}")
                break

            elif msg.type == web.WSMsgType.CLOSE:
                 logger.debug("WebSocket client initiated close")
                 break

    except asyncio.CancelledError:
         logger.info("WebSocket handler task cancelled.")
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}", exc_info=True)
    finally:
        with ws_clients_lock:
            ws_clients.discard(ws)
        logger.info(f"WebSocket client disconnected - {len(ws_clients)} active remain")

    return ws

async def index(request):
    """Serves the main HTML template."""
    logger.debug("Serving index page request.")
    template = request.app['jinja_env'].get_template('template.html')
    rendered = template.render(gridState=json.dumps(current_grid_state))
    return web.Response(text=rendered, content_type='text/html')


async def broadcast_bytes(data_bytes):
    """Broadcast data (bytes) to all connected WebSocket clients. Runs in web_loop."""
    global ws_clients, ws_clients_lock
    if not web_loop or web_loop != asyncio.get_running_loop():
         logger.error("broadcast_bytes called outside the web server's event loop!")
         return

    try:
        data_str = data_bytes.decode("utf-8")
        #logger.debug(f"Attempting to broadcast: {data_str[:100]}...")

        clients_to_send = set()
        with ws_clients_lock:
            clients_to_send = ws_clients.copy()

        if not clients_to_send:
            #logger.debug("No clients connected, skipping broadcast.")
            return

        active_clients = 0
        disconnected_clients = set()

        for ws in clients_to_send:
            try:
                if not ws.closed:
                    await ws.send_str(data_str)
                    active_clients += 1
                else:
                    disconnected_clients.add(ws)
            except asyncio.CancelledError:
                 logger.warning("Send operation cancelled for a client.")
                 disconnected_clients.add(ws)
            except Exception as e:
                # This can get noisy if a client disconnects uncleanly
                logger.debug(f"Error sending to client during broadcast (likely disconnected): {e}")
                disconnected_clients.add(ws)

        if disconnected_clients:
             with ws_clients_lock:
                  for ws in disconnected_clients:
                       ws_clients.discard(ws)
             logger.info(f"Removed {len(disconnected_clients)} disconnected clients after broadcast.")

        #logger.debug(f"Broadcast complete to {active_clients} active clients")

    except UnicodeDecodeError:
         logger.error("Error decoding bytes to UTF-8 in broadcast_bytes. Data not sent.")
    except Exception as e:
        logger.error(f"Unexpected error in broadcast_bytes: {e}", exc_info=True)


def asset_url(asset):
    """Placeholder for asset URL generation."""
    return f"/resources/{asset}"

def start_background_webserver():
    """Initializes and starts the aiohttp web server in a separate thread."""
    async def init_app():
        load_grid_state_from_file() # Load state before server starts

        app = web.Application()
        # Uncomment for debugging if needed, otherwise keep it off
        # aiohttp_debugtoolbar.setup(app, intercept_redirects=True, hosts=['127.0.0.1', '::1'])

        template_path = os.path.join(os.path.dirname(__file__), "..", "resources")
        app['jinja_env'] = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_path),
            autoescape=True
        )
        app['jinja_env'].globals['asset_url'] = asset_url

        app.router.add_get('/', index)
        app.router.add_get('/ws', websocket_handler)
        app.router.add_static('/resources/', path=template_path, name='resources')
        app.router.add_static('/build/',
            path=os.path.join(os.path.dirname(__file__), "..", "resources/build"),
            name='build', show_index=False, append_version=True) # show_index=False recommended

        ALLOWED_IMAGE_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "nodes", "eyes", "gif_sync"))
        logger.info(f"Configured allowed image base directory: {ALLOWED_IMAGE_BASE_DIR}")

        async def get_image(request):
            """Serve images ONLY from within the ALLOWED_IMAGE_BASE_DIR."""
            path_param = request.query.get('path')

            if not path_param:
                return web.Response(text="Missing 'path' parameter", status=400)

            # Basic check for obviously malicious characters (optional but good)
            if '..' in path_param:
                 logger.warning(f"Rejected image path containing '..': {path_param}")
                 return web.Response(text="Invalid path component", status=403)

            # Normalize the input path and make it absolute *relative to the current working directory*
            # This is often NOT what we want if the input is already absolute or relative to a different base
            # Instead, let's try to resolve it safely relative to our base dir, or just use the input if absolute
            # A safer approach combines the base dir with the filename part of the input path

            try:
                # Method 1: Assume path_param MIGHT be relative to base_dir OR absolute but intended to be inside base_dir
                # Resolve the input path absolutely
                requested_abs_path = os.path.abspath(path_param)

                # *** CRUCIAL SECURITY CHECK ***
                # Check if the resolved absolute path starts with the allowed base directory path
                # os.path.commonpath is safer for symbolic links etc. but startswith is often sufficient
                if not requested_abs_path.startswith(ALLOWED_IMAGE_BASE_DIR):
                    logger.error(f"Forbidden access attempt: Resolved path '{requested_abs_path}' is outside allowed base '{ALLOWED_IMAGE_BASE_DIR}'")
                    return web.Response(text="Access denied", status=403)

                # Secondary check: Ensure it's an actual file (prevents requesting directories)
                if not os.path.isfile(requested_abs_path):
                     logger.warning(f"Attempt to access non-file path: {requested_abs_path}")
                     return web.Response(text="Path is not a file", status=404) # Or 403

                # Check file extension *after* verifying path safety
                if not requested_abs_path.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                    logger.warning(f"Attempt to access non-image file type: {requested_abs_path}")
                    return web.Response(text="Only image files are allowed", status=403)

                # If all checks pass, serve the file
                logger.debug(f"Serving image: {requested_abs_path}") # Log only at debug level
                extension = os.path.splitext(requested_abs_path)[1].lower()
                content_type = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.png': 'image/png'}.get(extension, 'application/octet-stream')

                return web.FileResponse(
                    path=requested_abs_path,
                    headers={
                        'Content-Type': content_type,
                        'Cache-Control': 'max-age=3600',
                        'Access-Control-Allow-Origin': '*' # Consider if '*' is too permissive
                        }
                    )

            except ValueError as e: # Handles potential issues with path normalization on Windows with invalid chars
                 logger.error(f"Invalid character in path parameter '{path_param}': {e}")
                 return web.Response(text="Invalid path parameter", status=400)
            except Exception as e:
                logger.error(f"Error serving image '{path_param}': {str(e)}", exc_info=True)
                return web.Response(text="Error serving image", status=500)
            app.router.add_get('/get-image', get_image)
            # --- End Security Warning ---

        async def eye_proxy(request):
             # (Keep eye_proxy logic as is, logging errors is sufficient)
            ip = request.query.get('ip')
            filename = request.query.get('filename')
            if not ip or not filename: return web.Response(text="Missing 'ip' or 'filename' parameter", status=400)
            url = f"http://{ip}/playgif?name={filename}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        return web.Response(text=await response.text(), status=response.status, headers={'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*'})
            except Exception as e:
                logger.error(f"Error proxying request to eye display {ip}: {str(e)}")
                return web.Response(text=f"Error communicating with eye display: {str(e)}", status=500, headers={'Access-Control-Allow-Origin': '*'})
        app.router.add_get('/eye-proxy', eye_proxy)

        cert_file = os.path.join(os.path.dirname(__file__), "..", "cert.pem")
        key_file = os.path.join(os.path.dirname(__file__), "..", "key.pem")
        ssl_context = None
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            logger.info("Generating self-signed certificates...")
            try:
                subprocess.run([
                    "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
                    "-keyout", key_file, "-out", cert_file, "-days", "365", "-subj", "/CN=localhost"
                ], check=True, capture_output=True)
                logger.info("Self-signed certificates generated.")
            except Exception as e:
                 logger.error(f"Failed to generate self-signed certificates: {e}. Proceeding without HTTPS.", exc_info=True)

        if os.path.exists(cert_file) and os.path.exists(key_file):
             try:
                 ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                 ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)
                 logger.debug("SSL context loaded.")
             except Exception as e:
                 logger.error(f"Failed to load SSL certificates: {e}. Proceeding without HTTPS.", exc_info=True)
                 ssl_context = None
        else:
             logger.warning("Certificate files not found. Proceeding without HTTPS.")

        runner = web.AppRunner(app)
        await runner.setup()
        port = WEBSERVER_PORT_HTTPS if ssl_context else WEBSERVER_PORT_HTTP
        site = web.TCPSite(runner, '0.0.0.0', port, ssl_context=ssl_context)
        await site.start()
        protocol = "https" if ssl_context else "http"
        logger.info(f"Web server started on {protocol}://0.0.0.0:{port}")
        return runner

    def run_loop():
        global web_loop
        runner = None
        loop = asyncio.new_event_loop()
        web_loop = loop
        asyncio.set_event_loop(loop)
        try:
             runner = loop.run_until_complete(init_app())
             if runner: loop.run_forever()
        except KeyboardInterrupt: pass # Allow clean shutdown
        finally:
             if runner:
                  logger.info("Cleaning up web server...")
                  loop.run_until_complete(runner.cleanup())
             loop.close()
             logger.info("Web server event loop closed.")

    thread = threading.Thread(target=run_loop, name="WebServerThread", daemon=True)
    thread.start()
    return thread

def main():
    global grid_state_dirty, last_grid_state_save_time

    logger.info("Starting main application node...")
    web_thread = start_background_webserver()
    try:
        node = Node()
    except NameError:
         logger.critical("Dora Node class not defined. Exiting.")
         return # Exit if Node couldn't be imported or defined

    profile_manager = GamepadProfileManager()
    last_profiles_broadcast = 0

    logger.info("Entering main event loop...")
    try:
        for event in node:
            try:
                event_type = event.get("type")
                event_id = event.get("id")

                if event_type == "INPUT" and event_id == "tick":
                    flush_web_inputs(node, profile_manager)
                    current_time = time.time()

                    if grid_state_dirty and (current_time - last_grid_state_save_time > GRID_STATE_SAVE_INTERVAL):
                        logger.debug("Periodic save triggered for dirty grid state.")
                        save_grid_state_to_file()

                    if current_time - last_profiles_broadcast > 5:
                        try:
                            emit_profiles_list(node, profile_manager)
                            full_profiles = profile_manager.list_profiles()
                            response = {"id": "gamepad_profiles_list", "value": full_profiles, "type": "EVENT"}
                            serialized = json.dumps(response, default=str).encode('utf-8')
                            if web_loop: asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
                            logger.debug(f"Broadcasted profiles list ({len(full_profiles)} profiles)")
                            last_profiles_broadcast = current_time
                        except Exception as e:
                            logger.error(f"Error broadcasting profiles list: {e}", exc_info=True)

                elif event_type == "INPUT":
                    logger.debug(f"Received input event: ID={event_id}")
                    event_value_pa = event.get('value')
                    event_value = None
                    if event_value_pa is not None:
                         try:
                             if hasattr(event_value_pa, 'to_pylist'): event_value = event_value_pa.to_pylist()
                             elif hasattr(event_value_pa, 'as_py'): event_value = event_value_pa.as_py()
                             else: event_value = event_value_pa
                         except Exception as e:
                              logger.error(f"Error converting PyArrow value for event '{event_id}': {e}")
                              continue

                    # --- Handle Specific Handlers ---
                    handler_map = {
                        "save_gamepad_profile": handle_save_gamepad_profile,
                        "get_gamepad_profile": handle_get_gamepad_profile,
                        "check_gamepad_profile": handle_check_gamepad_profile,
                        "delete_gamepad_profile": handle_delete_gamepad_profile,
                        "list_gamepad_profiles": handle_list_gamepad_profiles,
                    }
                    if event_id in handler_map:
                        logger.debug(f"Handling specific event: '{event_id}'")
                        handler_map[event_id](event, node, profile_manager)
                        if event_id in ["save_gamepad_profile", "delete_gamepad_profile"]:
                            emit_profiles_list(node, profile_manager) # Update lists after change
                        continue # Skip generic broadcast

                    # --- Generic Input Event Broadcasting ---
                    if event_id == "power/runtime":
                        # (Runtime sanitization logic kept as is)
                        if event_value and isinstance(event_value, list) and len(event_value) > 0:
                            try:
                                runtime_val = float(event_value[0])
                                if runtime_val < 0 or math.isinf(runtime_val) or math.isnan(runtime_val): event_value[0] = 0
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error processing runtime value '{event_value[0]}': {e}. Resetting to 0.")
                                event_value[0] = 0
                        else: event_value = [0]

                    ws_event_id = event_id
                    if ws_event_id and ws_event_id.startswith("waveshare_servo/"):
                        ws_event_id = ws_event_id.replace("waveshare_servo/", "")

                    ws_event_value = event_value

                    # Attempt to fix JSON-in-string for servo events
                    is_servo_list = event_id in ["waveshare_servo/servos_list", "servos_list"]
                    is_servo_status = event_id in ["waveshare_servo/servo_status", "servo_status"]
                    if is_servo_list or is_servo_status:
                         if ws_event_value and len(ws_event_value) == 1 and isinstance(ws_event_value[0], str):
                              maybe_json_string = ws_event_value[0]
                              try:
                                   if maybe_json_string.strip().startswith(('[', '{')):
                                        parsed_value = json.loads(maybe_json_string)
                                        ws_event_value = parsed_value
                                        logger.debug(f"Parsed JSON-in-string for event '{event_id}'.")
                              except json.JSONDecodeError:
                                   logger.warning(f"Value for '{event_id}' looked like JSON but failed to parse: {maybe_json_string[:100]}...")
                              except Exception as e:
                                   logger.error(f"Unexpected error parsing potential JSON string for '{event_id}': {e}")

                         # Log servo count for list, suppress individual status logs at INFO
                         if is_servo_list:
                              count = 0
                              if isinstance(ws_event_value, list):
                                   count = len(ws_event_value)
                              logger.info(f"Broadcasting servos list: {count} servos found.")
                         # elif is_servo_status:
                         #      logger.debug(f"Broadcasting servo status update.") # Only log status at DEBUG


                    event_data_for_ws = {"id": ws_event_id, "value": ws_event_value, "type": "EVENT"}

                    try:
                        serialized = json.dumps(event_data_for_ws, default=str).encode('utf-8')
                        if web_loop: asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
                    except TypeError as e:
                         logger.error(f"Failed to serialize event data for WS broadcast (ID: {ws_event_id}): {e}. Value sample: {str(ws_event_value)[:100]}")
                    except Exception as e:
                         logger.error(f"Error scheduling broadcast for event (ID: {ws_event_id}): {e}")


                elif event_type == "STOP":
                    logger.info("Received STOP event. Exiting main loop.")
                    break
                elif event_type == "ERROR":
                    logger.error(f"Received ERROR event from Dora: {event.get('error')}")

            except Exception as e:
                logger.error(f"Error handling Dora event: {e}", exc_info=True)
                logger.error(f"Problematic event data sample: {str(event)[:200]}")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
    finally:
        logger.info("Exiting main function.")
        if grid_state_dirty:
            logger.info("Performing final save of grid state before exiting...")
            save_grid_state_to_file()

        if web_loop and web_loop.is_running():
            logger.info("Requesting web server event loop to stop...")
            web_loop.call_soon_threadsafe(web_loop.stop)
            if web_thread:
                 web_thread.join(timeout=2.0)
                 if web_thread.is_alive(): logger.warning("Web server thread did not exit cleanly.")

        logger.info("Application finished.")


if __name__ == "__main__":
    main()