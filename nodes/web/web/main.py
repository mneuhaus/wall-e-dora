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

logging.basicConfig(level=logging.DEBUG)

global_web_inputs = []
ws_clients = set()
web_loop = None

def flush_web_inputs(node):
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
        
        # Send initial servo data if available
        try:
            # Send a SCAN request to get current servo status
            logging.info("Sending SCAN request for new client connection")
            global_web_inputs.append({"output_id": "SCAN", "data": [], "metadata": {}})
            
            # Provide fallback data in case servos are not connected, using calibrated limits
            servo_data = [
                {"id": 13, "position": 500, "speed": 100, "min_pos": 100, "max_pos": 4000},
                {"id": 5, "position": 800, "speed": 100, "min_pos": 100, "max_pos": 4000}
            ]
            
            status_msg = {
                "id": "servo_status",
                "value": servo_data,
                "type": "EVENT"
            }
            await ws.send_str(json.dumps(status_msg))
            logging.info("Sent initial servo fallback data")
        except Exception as e:
            logging.error(f"Error sending initial servo data: {e}")
        
        # Process incoming messages
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    logging.debug(f"Received text message: {msg.data[:200]}...")
                    event = json.loads(msg.data)
                    output_id = event.get('output_id')
                    logging.info(f"Processed event with output_id: {output_id}")
                    
                    # Log additional details for joystick-related events
                    if output_id in ['save_joystick_servo', 'save_grid_state']:
                        if output_id == 'save_joystick_servo':
                            logging.info(f"Joystick servo assignment: {event.get('data')}")
                        elif output_id == 'save_grid_state':
                            # Find and log joystick widgets in the grid state
                            for widget_id, widget_data in event.get('data', {}).items():
                                if widget_data.get('type') == 'joystick-control':
                                    logging.info(f"Grid state update for joystick {widget_id}: x={widget_data.get('xServoId')}, y={widget_data.get('yServoId')}")
                    
                    global_web_inputs.append(event)
                    
                    # Handle immediate feedback for some messages
                    if event.get("output_id") == "SCAN":
                        logging.info("Received SCAN request from client")
                        # Send servo data immediately
                        servo_data = [
                            {"id": 13, "position": 500, "speed": 100, "min_pos": 100, "max_pos": 4000},
                            {"id": 5, "position": 800, "speed": 100, "min_pos": 100, "max_pos": 4000}
                        ]
                                    
                        status_msg = {
                            "id": "servo_status",
                            "value": servo_data, 
                            "type": "EVENT"
                        }
                        await ws.send_str(json.dumps(status_msg))
                        logging.info("SCAN response sent with fallback servo data")
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
    
    for event in node:
        try:
            if event["type"] == "INPUT" and "id" in event and (event["id"] == "tick"):
                flush_web_inputs(node)
            elif event["type"] == "INPUT":
                logging.info(f"Received input event: {event['id']}")
                event_value = event['value'].to_pylist()
                
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
                
                event_data = {
                    "id": event["id"],
                    "value": event_value,
                    "type": "EVENT"
                }
                
                # Store servo status data when we get it
                if event["id"] == "waveshare_servo/servo_status":
                    # Log minimal info about servos
                    if event_value:
                        servo_ids = [s.get('id') for s in event_value]
                        logging.info(f"Servo status update: {len(event_value)} servos {servo_ids}")
                    else:
                        logging.warning("Received empty servo status update")
                    
                serialized = json.dumps(event_data, default=str).encode('utf-8')
                if web_loop is not None:
                    asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
        except Exception as e:
            logging.error(f"Error handling event: {e}")


if __name__ == "__main__":
    main()
