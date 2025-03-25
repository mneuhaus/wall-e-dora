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

logging.basicConfig(level=logging.DEBUG)

global_web_inputs = []
ws_clients = set()
web_loop = None

def flush_web_inputs(node, profile_manager):
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

async def websocket_handler(request):
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
        logging.info("Sent welcome message to client")
        
        # Process incoming messages
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    logging.debug(f"Received text message: {msg.data[:200]}...")
                    event = json.loads(msg.data)
                    output_id = event.get('output_id')
                    logging.info(f"Processed event with output_id: {output_id}")
                    
                    # Log additional details for joystick-related and config-related events
                    if output_id in ['save_joystick_servo', 'save_grid_state', 'update_setting']:
                        if output_id == 'save_joystick_servo':
                            logging.info(f"Joystick servo assignment: {event.get('data')}")
                        elif output_id == 'save_grid_state':
                            # Find and log joystick widgets in the grid state
                            for widget_id, widget_data in event.get('data', {}).items():
                                if widget_data.get('type') == 'joystick-control':
                                    logging.info(f"Grid state update for joystick {widget_id}: x={widget_data.get('xServoId')}, y={widget_data.get('yServoId')}")
                        elif output_id == 'update_setting':
                            logging.info(f"Config update: {event.get('data')}")
                    
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

async def index(request):
    import os, json
    template = request.app['jinja_env'].get_template('template.html')
    # Load grid state from file if it exists
    grid_state = {}
    grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")

    if os.path.exists(grid_state_path):
        try:
            with open(grid_state_path, "r", encoding="utf-8") as f:
                grid_state = json.load(f)
        except Exception as e:
            print(f"Error loading grid state for template: {e}")

    # We set this as a JSON string in the template to initialize the frontend immediately
    rendered = template.render(gridState=json.dumps(grid_state))
    return web.Response(text=rendered, content_type='text/html')

async def broadcast_bytes(data_bytes):
    """Broadcast data to all connected WebSocket clients"""
    try:
        data_str = data_bytes.decode("utf-8")
        
        # Enhance logging for servo-related events
        if '"id":"servo_status"' in data_str or '"id":"servos_list"' in data_str:
            logging.info(f"Broadcasting servo data to {len(ws_clients)} clients: {data_str[:200]}...")
        else:
            logging.debug(f"Broadcasting to {len(ws_clients)} clients: {data_str[:100]}...")
            
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
                
        # Enhanced logging for servo data
        if '"id":"servo_status"' in data_str or '"id":"servos_list"' in data_str:
            logging.info(f"Servo data broadcast complete to {active_clients} active clients")
        else:
            logging.debug(f"Broadcast complete to {active_clients} active clients")
    except Exception as e:
        logging.error(f"Error in broadcast_bytes: {e}")

def asset_url(asset):
    return asset

def start_background_webserver():
    async def init_app():
        import os
        import jinja2
        import json

        app = web.Application()
        aiohttp_debugtoolbar.setup(app, intercept_redirects=True, hosts=['127.0.0.1', '::1'])
        template_path = os.path.join(os.path.dirname(__file__), "..", "resources")
        app['jinja_env'] = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
        app.router.add_get('/', index)
        app.router.add_get('/ws', websocket_handler)
        app.router.add_static('/resources/', path=template_path, name='resources')

        app.router.add_static('/build/',
            path=os.path.join(os.path.dirname(__file__), "..", "resources/build"),
            name='build',
            show_index=True,
            append_version=True
        )

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
    cmd = ['nodes/web/resources/node_modules/.bin/encore', 'dev', '--watch']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    def print_output():
        for line in iter(proc.stdout.readline, ""):
            print("[ASSET COMPILER]", line, end="")
    threading.Thread(target=print_output, daemon=True).start()

def main():
    # start_asset_compilation()
    start_background_webserver()
    node = Node()
    
    # Initialize gamepad profile manager
    profile_manager = GamepadProfileManager()
    
    for event in node:
        try:
            if event["type"] == "INPUT" and "id" in event and (event["id"] == "tick"):
                flush_web_inputs(node, profile_manager)
            elif event["type"] == "INPUT":
                logging.info(f"Received input event: {event['id']}")
                event_value = event['value'].to_pylist()
                
                # Handle gamepad profile events
                if event["id"] == "save_gamepad_profile":
                    handle_save_gamepad_profile(event, node, profile_manager)
                    print(f"Saved gamepad profile: {event['value'][0]}")
                    print(f"Profiles storage directory: {profile_manager.profiles_dir}")
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
