from dora import Node
import pyarrow as pa
import threading
import asyncio
import queue
import os
import jinja2
from aiohttp import web
import logging
logging.basicConfig(level=logging.DEBUG)
import aiohttp_debugtoolbar

bg_log_queue = queue.Queue()

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            bg_log_queue.put(msg)
        except Exception:
            self.handleError(record)

def flush_bg_logs():
    while True:
        try:
            msg = bg_log_queue.get(timeout=1)
            print("BG_LOG:", msg)
        except queue.Empty:
            continue

global_web_inputs = []
latest_power_metrics = {}
latest_available_sounds = []
latest_volume = 1.0
ws_clients = set()
web_loop = None

def flush_web_inputs(node):
    global global_web_inputs
    if not global_web_inputs:
        return
    import json, pyarrow as pa
    for web_event in global_web_inputs:
        node.send_output(output_id="web_input", data=pa.array([json.dumps(web_event)]), metadata={})
    global_web_inputs = []

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients.add(ws)
    try:
        async for msg in ws:
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
    template = request.app['jinja_env'].get_template('template.html')
    rendered = template.render()
    return web.Response(text=rendered, content_type='text/html')

async def broadcast_bytes(data_bytes):
    for ws in ws_clients.copy():
        if not ws.closed:
            await ws.send_bytes(data_bytes)
        else:
            ws_clients.discard(ws)

def start_background_webserver():
    async def init_app():
        app = web.Application()
        import os
        import jinja2
        aiohttp_debugtoolbar.setup(app, intercept_redirects=True, hosts=['127.0.0.1', '::1'])
        template_path = os.path.join(os.path.dirname(__file__), "..", "resources")
        app['jinja_env'] = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
        app.router.add_get('/', index)
        app.router.add_get('/ws', websocket_handler)
        app.router.add_static('/resources/', path=template_path, name='resources')
        js_path = os.path.join(os.path.dirname(__file__), "..", "resources/js")
        print(js_path)
        if os.path.exists(js_path):
            print("DEBUG: Static JS files found at: " + str(js_path))
            app.router.add_static('/js/', path=js_path, name='js', show_index=True, append_version=True)
        else:
            print("DEBUG: Static JS files NOT found at: " + str(js_path))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

    def run_loop():
        global web_loop
        loop = asyncio.new_event_loop()
        web_loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_app())
        print("DEBUG: Web server started on port 8080")
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

def main():
    start_background_webserver()
    bg_thread = threading.Thread(target=flush_bg_logs, daemon=True)
    bg_thread.start()
    node = Node()
    
    for event in node:
        if event["type"] == "INPUT":
            import pyarrow as pa
            def convert(val):
                if "NodeCleanupHandle" in str(type(val)):
                    return None
                if hasattr(val, "as_py"):
                    try:
                        return val.as_py()
                    except Exception:
                        return str(val)
                if isinstance(val, (int, float, str, bool)):
                    return val
                return str(val)
            event_converted = {k: cv for k, cv in ((k, convert(v)) for k, v in event.items()) if cv is not None}
            batch = pa.RecordBatch.from_pydict({ k: [event_converted[k]] for k in event_converted })
            sink = pa.BufferOutputStream()
            writer = pa.ipc.RecordBatchStreamWriter(sink, batch.schema)
            writer.write_batch(batch)
            writer.close()
            serialized = sink.getvalue().to_pybytes()
            if web_loop is not None:
                asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
        elif "id" in event and event["id"] == "tick":
            flush_web_inputs(node)


if __name__ == "__main__":
    main()
