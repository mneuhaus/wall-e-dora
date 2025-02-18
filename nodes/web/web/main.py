from dora import Node
import threading
import asyncio
import os
import jinja2
from aiohttp import web
import aiohttp_debugtoolbar
import json
import logging
import pyarrow as pa
import subprocess

logging.basicConfig(level=logging.DEBUG)

global_web_inputs = []
ws_clients = set()
web_loop = None

def flush_web_inputs(node):
    global global_web_inputs
    if not global_web_inputs:
        return
    import os, json
    for web_event in global_web_inputs:
        if web_event.get("output_id") == "save_grid_state":
            grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")
            with open(grid_state_path, "w", encoding="utf-8") as f:
                json.dump(web_event["data"], f)
        else:
            node.send_output(
                output_id=web_event["output_id"], data=pa.array(web_event["data"]), metadata=web_event["metadata"]
            )
    global_web_inputs = []

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients.add(ws)
    try:
        async for msg in ws:
            print(msg)
            if msg.type == web.WSMsgType.TEXT:
                try:
                    import json
                    event = json.loads(msg.data)
                    global_web_inputs.append(event)
                except Exception:
                    global_web_inputs.append({"raw": msg.data})
            elif msg.type == web.WSMsgType.BINARY:
                try:
                    import pyarrow as pa
                    buf = pa.BufferReader(msg.data)
                    batch = pa.ipc.read_record_batch(buf)
                    row = {k: v[0] for k, v in batch.to_pydict().items()}
                    global_web_inputs.append(row)
                except Exception as e:
                    print("Error processing binary websocket message", e)
    finally:
        ws_clients.discard(ws)
    return ws

async def index(request):
    import os, json
    template = request.app['jinja_env'].get_template('template.html')
    # Load grid state from file if it exists
    grid_state = None
    grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")

    if os.path.exists(grid_state_path):
        with open(grid_state_path, "r", encoding="utf-8") as f:
            grid_state = json.load(f)

    rendered = template.render(gridState=json.dumps(grid_state))
    return web.Response(text=rendered, content_type='text/html')

async def broadcast_bytes(data_bytes):
    for ws in ws_clients.copy():
        if not ws.closed:
            await ws.send_str(data_bytes.decode("utf-8"))
        else:
            ws_clients.discard(ws)

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
        if event["type"] == "INPUT" and "id" in event and event["id"] == "change_servo_id":
            handle_change_servo_id_event(event)
        elif event["type"] == "INPUT" and "id" in event and (event["id"] == "tick" or event["id"] == "runtime"):
            flush_web_inputs(node)
        elif event["type"] == "INPUT":
            event['value'] = event['value'].to_pylist()
            serialized = json.dumps(event, default=str).encode('utf-8')
            if web_loop is not None:
                asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)


if __name__ == "__main__":
    main()
