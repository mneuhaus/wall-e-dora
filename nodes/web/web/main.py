"""Main module for the Web Node.

Sets up an aiohttp web server with WebSocket support to serve the React frontend
and handle real-time communication with clients and other Dora nodes.
Manages gamepad profiles and orchestrates data flow between the UI and backend nodes.
"""

from dora import Node
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
from handlers.gamepad_profiles import (
    GamepadProfileManager,
    handle_save_gamepad_profile,
    handle_get_gamepad_profile,
    handle_check_gamepad_profile,
    handle_delete_gamepad_profile,
    handle_list_gamepad_profiles,
    emit_profiles_list
)

logging.basicConfig(level=logging.INFO)

# Global variables (consider refactoring into a class or context)
global_web_inputs = []  # Queue for events received from WebSocket clients
ws_clients = set()      # Set of active WebSocket client connections
web_loop = None         # asyncio event loop for the web server thread


def flush_web_inputs(node: Node, profile_manager: GamepadProfileManager):
    """Process queued events received from WebSocket clients.

    Iterates through `global_web_inputs`, handles special events like saving
    grid state or joystick settings locally, and forwards other events
    to the appropriate Dora outputs.

    Args:
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance (unused here but
                         passed for consistency).
    """
    global global_web_inputs
    if not global_web_inputs:
        return
    import os, json
    logging.info(f"Processing {len(global_web_inputs)} web events")
    for web_event in global_web_inputs:
        if web_event.get("output_id") == "save_grid_state":
            grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")
            with open(grid_state_path, "w", encoding="utf-8") as f:
                json.dump(web_event["data"], f)

            # Broadcast the updated grid state to all connected clients
            for ws in ws_clients.copy():
                if not ws.closed:
                    try:
                        response = {
                            "id": "grid_state",
                            "value": web_event["data"],
                            "type": "EVENT"
                        }
                        asyncio.run_coroutine_threadsafe(
                            ws.send_str(json.dumps(response)),
                            web_loop
                        )
                    except Exception as e:
                        print(f"Error broadcasting grid state: {e}")
                else:
                    ws_clients.discard(ws)

        elif web_event.get("output_id") == "save_joystick_servo":
            # Handle joystick servo selection persistence
            widget_id = web_event.get("data", {}).get("id")
            axis = web_event.get("data", {}).get("axis")
            servo_id = web_event.get("data", {}).get("servoId")

            if widget_id and axis in ['x', 'y']:
                # Load current grid state
                grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")
                grid_state = {}
                if os.path.exists(grid_state_path):
                    try:
                        with open(grid_state_path, "r", encoding="utf-8") as f:
                            grid_state = json.load(f)
                    except Exception as e:
                        print(f"Error loading grid state: {e}")

                # Update the widget with the new servo ID
                if widget_id in grid_state:
                    # Update the appropriate servo ID property
                    servo_prop = f"{axis}ServoId"
                    grid_state[widget_id][servo_prop] = servo_id

                    # Save the updated grid state
                    with open(grid_state_path, "w", encoding="utf-8") as f:
                        json.dump(grid_state, f)

                    # Broadcast the updated grid state
                    for ws in ws_clients.copy():
                        if not ws.closed:
                            try:
                                response = {
                                    "id": "grid_state",
                                    "value": grid_state,
                                    "type": "EVENT"
                                }
                                asyncio.run_coroutine_threadsafe(
                                    ws.send_str(json.dumps(response)),
                                    web_loop
                                )
                            except Exception as e:
                                print(f"Error broadcasting updated joystick state: {e}")
                        else:
                            ws_clients.discard(ws)

                    print(f"Updated joystick {widget_id} {axis}-axis to servo {servo_id}")
                else:
                    print(f"Cannot update joystick {widget_id}: widget not found in grid state")

        elif web_event.get("output_id") == "get_grid_state":
            # Load and send grid state to the requesting client
            grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")
            grid_state = {}

            if os.path.exists(grid_state_path):
                try:
                    with open(grid_state_path, "r", encoding="utf-8") as f:
                        grid_state = json.load(f)
                except Exception as e:
                    print(f"Error loading grid state: {e}")

            # Send to the client that requested it
            for ws in ws_clients.copy():
                if not ws.closed:
                    try:
                        response = {
                            "id": "grid_state",
                            "value": grid_state,
                            "type": "EVENT"
                        }
                        asyncio.run_coroutine_threadsafe(
                            ws.send_str(json.dumps(response)),
                            web_loop
                        )
                    except Exception as e:
                        print(f"Error sending grid state: {e}")
                else:
                    ws_clients.discard(ws)
        else:
            node.send_output(
                output_id=web_event["output_id"], data=pa.array(web_event["data"]), metadata=web_event["metadata"]
            )
    global_web_inputs = []


async def websocket_handler(request: web.Request):
    """Handle incoming WebSocket connections and messages.

    Manages the lifecycle of a WebSocket connection, receives messages
    from the client, queues them for processing by `flush_web_inputs`,
    and removes the client upon disconnection.

    Args:
        request: The aiohttp request object.

    Returns:
        The WebSocketResponse object.
    """
    logging.info("New WebSocket connection request received")
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Add to clients
    ws_clients.add(ws)
    logging.info(f"WebSocket connection established - {len(ws_clients)} active connections")

    # Send connection confirmation
    try:
        welcome_msg = {
            "id": "connection_status",
            "value": {"status": "connected", "timestamp": time.time()},
            "type": "EVENT"
        }
        await ws.send_str(json.dumps(welcome_msg))

        # Process incoming messages
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    event = json.loads(msg.data)
                    output_id = event.get('output_id')
                    logging.debug(f"Processed event with output_id: {output_id}")

                    # More detailed logging only for important configuration changes
                    if output_id in ['save_joystick_servo']:
                        logging.info(f"Joystick servo assignment: {event.get('data')}")

                    global_web_inputs.append(event)
                except Exception as e:
                    logging.error(f"Error processing WebSocket text message: {e}")
                    global_web_inputs.append({"raw": msg.data})
            elif msg.type == web.WSMsgType.BINARY:
                try:
                    import pyarrow as pa
                    buf = pa.BufferReader(msg.data)
                    batch = pa.ipc.read_record_batch(buf)
                    row = {k: v[0] for k, v in batch.to_pydict().items()}
                    global_web_inputs.append(row)
                except Exception as e:
                    logging.error(f"Error processing binary websocket message: {e}")
            elif msg.type == web.WSMsgType.ERROR:
                logging.error(f"WebSocket connection closed with exception {ws.exception()}")
    except Exception as e:
        logging.error(f"WebSocket handler error: {e}")
    finally:
        ws_clients.discard(ws)
        logging.info(f"WebSocket connection closed - {len(ws_clients)} active connections remain")

    return ws


async def index(request: web.Request):
    """Serve the main HTML template for the React frontend.

    Renders `template.html` using Jinja2. Currently injects an empty
    grid state, as the state is primarily managed via WebSocket.

    Args:
        request: The aiohttp request object.

    Returns:
        An aiohttp web Response object containing the rendered HTML.
    """
    import os, json
    template = request.app['jinja_env'].get_template('template.html')
    # For fixed layout, we don't need to load grid state
    rendered = template.render(gridState=json.dumps({}))
    return web.Response(text=rendered, content_type='text/html')


async def broadcast_bytes(data_bytes: bytes):
    """Broadcast binary data (decoded as UTF-8 string) to all connected WebSocket clients.

    Args:
        data_bytes: The bytes object containing the message to broadcast.
    """
    try:
        data_str = data_bytes.decode("utf-8")

        # Reduce logging for common events
        if '"id":"servo_status"' in data_str or '"id":"servos_list"' in data_str:
            logging.debug(f"Broadcasting servo data to {len(ws_clients)} clients")
        else:
            logging.debug(f"Broadcasting to {len(ws_clients)} clients: {data_str[:50]}...")

        active_clients = 0

        for ws in ws_clients.copy():
            try:
                if not ws.closed:
                    await ws.send_str(data_str)
                    active_clients += 1
                else:
                    ws_clients.discard(ws)
            except Exception as e:
                logging.error(f"Error sending to client: {e}")
                ws_clients.discard(ws)

        # Minimal logging for broadcasts
        logging.debug(f"Broadcast complete to {active_clients} active clients")
    except Exception as e:
        logging.error(f"Error in broadcast_bytes: {e}")

def asset_url(asset):
    return asset


def start_background_webserver():
    """Initialize and start the aiohttp web server in a background thread."""
    async def init_app():
        """Async function to set up the aiohttp application."""
        import os
        import jinja2
        import json
        import aiohttp

        app = web.Application()
        aiohttp_debugtoolbar.setup(app, intercept_redirects=True, hosts=['127.0.0.1', '::1'])
        template_path = os.path.join(os.path.dirname(__file__), "..", "resources")
        app['jinja_env'] = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
        app.router.add_get('/', index)
        app.router.add_get('/ws', websocket_handler)
        app.router.add_static('/resources/', path=template_path, name='resources')
        
        # Add specific route for icons with correct MIME types
        app.router.add_static('/icons/', 
            path=os.path.join(template_path, "icons"),
            name='icons', 
            show_index=True,
            append_version=False
        )
        
        # Add specific route for screenshots
        app.router.add_static('/screenshots/', 
            path=os.path.join(template_path, "screenshots"),
            name='screenshots', 
            show_index=True,
            append_version=False
        )
        
        # Add special route for manifest.webmanifest with correct MIME type
        async def serve_manifest(request):
            manifest_path = os.path.join(template_path, "manifest.webmanifest")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    content = f.read()
                return web.Response(text=content, content_type="application/manifest+json")
            return web.Response(status=404)
        
        app.router.add_get('/manifest.webmanifest', serve_manifest)
        
        # Add special route for service-worker.js with correct MIME type
        async def serve_service_worker(request):
            sw_path = os.path.join(template_path, "service-worker.js")
            if os.path.exists(sw_path):
                with open(sw_path, 'r') as f:
                    content = f.read()
                return web.Response(text=content, content_type="application/javascript")
            return web.Response(status=404)
            
        app.router.add_get('/service-worker.js', serve_service_worker)
        
        # Add handler for serving icon files with correct MIME type
        async def serve_icon(request):
            icon_name = request.match_info.get('icon')
            icon_path = os.path.join(template_path, "icons", icon_name)
            if os.path.exists(icon_path):
                # Log that we're trying to serve this icon
                logging.info(f"Serving icon: {icon_name} from {icon_path}")
                return web.FileResponse(
                    path=icon_path,
                    headers={
                        'Content-Type': 'image/png',
                        'Cache-Control': 'max-age=86400'
                    }
                )
            logging.error(f"Icon not found: {icon_name}")
            return web.Response(status=404)
            
        app.router.add_get('/icons/{icon}', serve_icon)
        
        # Add handler for serving screenshot files with correct MIME type
        async def serve_screenshot(request):
            screenshot_name = request.match_info.get('screenshot')
            screenshot_path = os.path.join(template_path, "screenshots", screenshot_name)
            if os.path.exists(screenshot_path):
                # Log that we're trying to serve this screenshot
                logging.info(f"Serving screenshot: {screenshot_name} from {screenshot_path}")
                return web.FileResponse(
                    path=screenshot_path,
                    headers={
                        'Content-Type': 'image/png',
                        'Cache-Control': 'max-age=86400'
                    }
                )
            logging.error(f"Screenshot not found: {screenshot_name}")
            return web.Response(status=404)
            
        app.router.add_get('/screenshots/{screenshot}', serve_screenshot)

        app.router.add_static('/build/',
            path=os.path.join(os.path.dirname(__file__), "..", "resources/build"),
            name='build',
            show_index=True,
            append_version=True
        )

        # Handler for serving images from arbitrary paths
        async def get_image(request):
            """Serve images from arbitrary file paths."""
            path = request.query.get('path')

            if not path:
                return web.Response(text="Missing 'path' parameter", status=400)

            # Basic security check to only allow image files
            if not path.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                return web.Response(text="Only image files are allowed", status=403)

            # Check if file exists
            if not os.path.exists(path):
                return web.Response(text=f"Image not found: {path}", status=404)

            try:
                # Determine content type based on file extension
                extension = os.path.splitext(path)[1].lower()
                content_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.png': 'image/png'
                }.get(extension, 'application/octet-stream')

                # Create a file response
                return web.FileResponse(
                    path=path,
                    headers={
                        'Content-Type': content_type,
                        'Cache-Control': 'max-age=3600',  # Cache for 1 hour
                        'Access-Control-Allow-Origin': '*'  # Allow cross-origin access
                    }
                )
            except Exception as e:
                logging.error(f"Error serving image {path}: {str(e)}")
                return web.Response(text=f"Error serving image: {str(e)}", status=500)

        # Add route for image serving
        app.router.add_get('/get-image', get_image)

        # Proxy endpoint for communicating with eye displays
        async def eye_proxy(request):
            """Proxy requests to eye displays."""
            ip = request.query.get('ip')
            filename = request.query.get('filename')

            if not ip or not filename:
                return web.Response(text="Missing 'ip' or 'filename' parameter", status=400)

            try:
                # Construct the request URL to the eye display
                url = f"http://{ip}/playgif?name={filename}"

                # Use aiohttp.ClientSession to make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        status = response.status
                        response_text = await response.text()

                        return web.Response(
                            text=response_text,
                            status=status,
                            headers={
                                'Content-Type': 'text/plain',
                                'Access-Control-Allow-Origin': '*'
                            }
                        )
            except Exception as e:
                logging.error(f"Error proxying request to eye display {ip}: {str(e)}")
                return web.Response(
                    text=f"Error communicating with eye display: {str(e)}",
                    status=500,
                    headers={'Access-Control-Allow-Origin': '*'}
                )

        # Add route for eye display proxy
        app.router.add_get('/eye-proxy', eye_proxy)

        import ssl
        import os
        import subprocess
        # Set the paths for the self-signed certificate and key
        cert_file = os.path.join(os.path.dirname(__file__), "..", "cert.pem")
        key_file = os.path.join(os.path.dirname(__file__), "..", "key.pem")
        # Generate self-signed certs if they do not exist
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            print("Generating self-signed certificates")
            subprocess.run([
                "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
                "-keyout", key_file, "-out", cert_file, "-days", "365", "-subj", "/CN=localhost"
            ], check=True)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8443, ssl_context=ssl_context)
        await site.start()

    def run_loop():
        global web_loop
        loop = asyncio.new_event_loop()
        web_loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_app())
        print("DEBUG: Web server started on port 8443")
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()


def start_asset_compilation():
    """Start the Webpack Encore asset compilation process in watch mode."""
    cmd = ['nodes/web/resources/node_modules/.bin/encore', 'dev', '--watch']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    def print_output():
        for line in iter(proc.stdout.readline, ""):
            print("[ASSET COMPILER]", line, end="")
    threading.Thread(target=print_output, daemon=True).start()


def main():
    """Main function for the Web Node.

    Starts the background web server, initializes the Dora node and the
    GamepadProfileManager, and enters the main Dora event loop to process
    incoming events from other nodes and the web UI.
    """
    # start_asset_compilation() # Usually run manually or via Makefile
    start_background_webserver()
    node = Node()

    # Initialize gamepad profile manager
    profile_manager = GamepadProfileManager()

    # Periodic profile list broadcasting
    last_profiles_broadcast = 0

    for event in node:
        try:
            if event["type"] == "INPUT" and "id" in event and (event["id"] == "tick"):
                # Process all pending web inputs
                flush_web_inputs(node, profile_manager)

                # Periodically broadcast gamepad profiles list
                current_time = time.time()
                if current_time - last_profiles_broadcast > 5:  # Every 5 seconds
                    try:
                        # Emit the updated list of profiles to Dora
                        emit_profiles_list(node, profile_manager)

                        # Send full profiles directly to WebSocket clients (not simplified)
                        full_profiles = profile_manager.list_profiles()

                        response = {
                            "id": "gamepad_profiles_list",
                            "value": full_profiles,
                            "type": "EVENT"
                        }

                        serialized = json.dumps(response, default=str).encode('utf-8')
                        asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
                        logging.info(f"Broadcasted profiles list to {len(ws_clients)} WebSocket clients")

                        last_profiles_broadcast = current_time
                    except Exception as e:
                        logging.error(f"Error broadcasting profiles list: {e}")
            elif event["type"] == "INPUT":
                logging.info(f"Received input event: {event['id']}")
                event_value = event['value'].to_pylist()

                # Handle gamepad profile events
                if event["id"] == "save_gamepad_profile":
                    print(f"DEBUG - main.py: Received save_gamepad_profile event")
                    print(f"DEBUG - main.py: Event data: {event}")
                    print(f"DEBUG - main.py: Value type: {type(event['value'])}")

                    if hasattr(event['value'], 'to_pylist'):
                        value_list = event['value'].to_pylist()
                        print(f"DEBUG - main.py: Value as pylist: {value_list}")
                    else:
                        print(f"DEBUG - main.py: Value doesn't have to_pylist method")

                    handle_save_gamepad_profile(event, node, profile_manager)
                    print(f"Saved gamepad profile: {event['value'][0] if hasattr(event['value'], '__getitem__') else event['value']}")
                    print(f"Profiles storage directory: {profile_manager.profiles_dir}")
                    print(f"DEBUG - main.py: Directory exists: {os.path.exists(profile_manager.profiles_dir)}")
                    # After saving, emit updated profiles list
                    emit_profiles_list(node, profile_manager)
                    continue
                elif event["id"] == "get_gamepad_profile":
                    handle_get_gamepad_profile(event, node, profile_manager)
                    continue
                elif event["id"] == "check_gamepad_profile":
                    handle_check_gamepad_profile(event, node, profile_manager)
                    continue
                elif event["id"] == "delete_gamepad_profile":
                    handle_delete_gamepad_profile(event, node, profile_manager)
                    continue
                elif event["id"] == "list_gamepad_profiles":
                    handle_list_gamepad_profiles(event, node, profile_manager)
                    continue

                # Add special handling for runtime values
                if event["id"] == "power/runtime":
                    logging.info(f"Runtime value received: {event_value} (type: {type(event_value)})")
                    # Ensure runtime value is a valid number
                    if event_value and isinstance(event_value, list):
                        try:
                            runtime_val = float(event_value[0])
                            if runtime_val <= 0 or math.isinf(runtime_val) or math.isnan(runtime_val):
                                event_value[0] = 0
                            logging.info(f"Processed runtime: {event_value[0]}")
                        except Exception as e:
                            logging.error(f"Error processing runtime value: {e}")
                            event_value[0] = 0

                # Create the event data with potentially modified ID
                event_id = event["id"]

                # Transform event IDs to match what the frontend expects
                if event_id.startswith("waveshare_servo/"):
                    event_id = event_id.replace("waveshare_servo/", "")
                    logging.info(f"Transformed event ID from {event['id']} to {event_id}")

                event_data = {
                    "id": event_id,
                    "value": event_value,
                    "type": "EVENT"
                }

                # Handle servo-related events
                if event["id"] == "waveshare_servo/servo_status" or event["id"] == "servo_status":
                    # Fix for json-in-string format for servo status updates
                    if event_value and len(event_value) == 1 and isinstance(event_value[0], str):
                        try:
                            # Check if it's a JSON string
                            if event_value[0].startswith('[{') or event_value[0].startswith('{'):
                                parsed_value = json.loads(event_value[0])
                                # Update the event_data with properly parsed value
                                event_value = parsed_value
                                event_data["value"] = parsed_value
                                logging.info(f"Fixed JSON-in-string format for servo_status")
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to parse servo_status JSON string: {e}")

                    # Log info about single servo update
                    if event_value:
                        if isinstance(event_value, list):
                            try:
                                servo_ids = [s.get('id') for s in event_value]
                                logging.info(f"Servo status update: {len(event_value)} servos {servo_ids}")
                            except (TypeError, AttributeError) as e:
                                logging.error(f"Error processing servo IDs in list: {e}, value: {event_value[:100]}")
                        else:
                            try:
                                # Single servo update
                                servo_id = event_value.get('id')
                                logging.info(f"Servo status update: servo {servo_id}")
                            except (TypeError, AttributeError) as e:
                                logging.error(f"Error processing single servo: {e}, value type: {type(event_value)}")
                    else:
                        logging.warning("Received empty servo status update")

                elif event["id"] == "waveshare_servo/servos_list" or event["id"] == "servos_list":
                    # Log info about servos list
                    if event_value:
                        # Detailed logging of raw event value for troubleshooting
                        logging.info(f"Raw servos_list event value type: {type(event_value)}, length: {len(event_value)}")
                        if len(event_value) > 0:
                            logging.info(f"First element type: {type(event_value[0])}")
                            if isinstance(event_value[0], str):
                                logging.info(f"First element content sample: {event_value[0][:100]}...")

                        # Fix for json-in-string format: if the first item is a string containing JSON
                        if len(event_value) == 1 and isinstance(event_value[0], str):
                            try:
                                # Case 1: String starts with an array of objects marker
                                if event_value[0].startswith('[{') or event_value[0].startswith('[{'):
                                    # Log the raw string for debugging
                                    logging.info(f"Raw servos_list JSON array string: {event_value[0][:200]}...")

                                    # Parse the JSON string into a proper list of objects
                                    parsed_value = json.loads(event_value[0])
                                    if isinstance(parsed_value, list):
                                        # Update the event data with properly parsed value
                                        event_value = parsed_value
                                        event_data["value"] = parsed_value
                                        logging.info(f"Successfully parsed servos_list array. Now contains {len(parsed_value)} servos.")
                                    else:
                                        logging.error(f"Parsed servos_list JSON is not a list. Got type: {type(parsed_value)}")

                                # Case 2: String starts with a single object marker (handle single servo case)
                                elif event_value[0].startswith('{'):
                                    logging.info(f"Raw servos_list single JSON object: {event_value[0][:200]}...")

                                    # Parse the JSON string into a single object
                                    parsed_value = json.loads(event_value[0])
                                    if isinstance(parsed_value, dict):
                                        # Create a list with this single servo
                                        event_value = [parsed_value]
                                        event_data["value"] = [parsed_value]
                                        logging.info(f"Successfully parsed single servo JSON into a list. ID: {parsed_value.get('id')}")
                                    else:
                                        logging.error(f"Parsed servos_list JSON object is not a dict. Got type: {type(parsed_value)}")
                            except json.JSONDecodeError as e:
                                logging.error(f"Failed to parse servos_list JSON string: {e}, string was: {event_value[0][:100]}...")

                        # Log the servo IDs
                        try:
                            # Check if event_value is a list of dicts or list of something else
                            if all(isinstance(item, dict) for item in event_value):
                                servo_ids = [s.get('id') for s in event_value]
                                logging.info(f"Servos list update: {len(event_value)} servos {servo_ids}")
                            else:
                                logging.error(f"event_value contains non-dict items: {event_value[:5]}")
                        except (TypeError, AttributeError) as e:
                            logging.error(f"Error processing servo IDs: {e}, value type: {type(event_value)}, value: {event_value}")
                    else:
                        logging.warning("Received empty servos list")


                # Handle config-related events
                elif event["id"] in ["config/setting_updated", "config/settings"]:
                    event_name = event["id"].replace("config/", "")
                    if event_name == "settings":
                        logging.info(f"Received complete settings")
                    else:
                        logging.info(f"Received config event: {event_name} with value: {event_value[:100] if len(str(event_value)) > 100 else event_value}")

                serialized = json.dumps(event_data, default=str).encode('utf-8')
                if web_loop is not None:
                    asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
        except Exception as e:
            logging.error(f"Error handling event: {e}")


if __name__ == "__main__":
    main()
