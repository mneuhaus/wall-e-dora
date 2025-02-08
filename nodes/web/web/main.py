from dora import Node
import pyarrow as pa
import threading
import asyncio
import queue
import os
import jinja2
from aiohttp import web


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
    for web_event in global_web_inputs:
        print("Processing web input:", web_event)
        if web_event.get("action") == "button":
            node.send_output(output_id="play_requested_sound", data=pa.array(["default_sound.mp3"]), metadata={})
        elif web_event.get("action") == "slider":
            try:
                slider_value = int(web_event.get("value"))
                node.send_output(output_id="slider_input", data=pa.array([slider_value]), metadata={})
            except ValueError:
                print("Invalid slider value received:", web_event.get("value"))
        elif web_event.get("action") == "set_volume":
            try:
                volume_value = float(web_event.get("value"))
                node.send_output(output_id="set_volume", data=pa.array([volume_value]), metadata={})
            except ValueError:
                print("Invalid volume value received:", web_event.get("value"))
        elif web_event.get("action") == "sound_click":
            print("Play sound clicked: " + web_event.get("value"))
            node.send_output(output_id="play_requested_sound", data=pa.array([web_event.get("value")]), metadata={})
    global_web_inputs = []

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients.add(ws)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    # Fallback for text messages
                    data = msg.data.strip().split(":")
                    if data[0] == "button":
                        global_web_inputs.append({"action": "button"})
                    elif data[0] == "slider" and len(data) > 1:
                        global_web_inputs.append({"action": "slider", "value": data[1]})
                    elif data[0] == "set_volume" and len(data) > 1:
                        global_web_inputs.append({"action": "set_volume", "value": data[1]})
                    elif data[0] == "sound_click" and len(data) > 1:
                        global_web_inputs.append({"action": "sound_click", "value": data[1]})
                except Exception as e:
                    print("Error processing text websocket message", e)
            elif msg.type == web.WSMsgType.BINARY:
                try:
                    import pyarrow as pa
                    buf = pa.BufferReader(msg.data)
                    batch = pa.ipc.read_record_batch(buf)
                    row = {k: v[0] for k, v in batch.to_pydict().items()}
                    if row.get("action") == "button":
                        global_web_inputs.append({"action": "button"})
                    elif row.get("action") == "slider" and "value" in row:
                        global_web_inputs.append({"action": "slider", "value": row["value"]})
                    elif row.get("action") == "sound_click" and "value" in row:
                        global_web_inputs.append({"action": "sound_click", "value": row["value"]})
                except Exception as e:
                    print("Error processing binary websocket message", e)
    finally:
        ws_clients.discard(ws)
    return ws

async def index(request):
    template = request.app['jinja_env'].get_template('template.html')
    rendered = template.render()
    return web.Response(text=rendered, content_type='text/html')

async def broadcast_power_metrics():
    import pyarrow as pa
    safe_metrics = {}
    for key, value in latest_power_metrics.items():
        if isinstance(value, float) and (value == float("inf") or value != value):
            safe_metrics[key] = "Infinity"
        else:
            safe_metrics[key] = value
    safe_metrics["available_sounds"] = latest_available_sounds
    safe_metrics["volume"] = latest_volume
    # Wrap each value in a list to form a record batch with one row
    batch = pa.RecordBatch.from_pydict({k: [v] for k, v in safe_metrics.items()})
    serialized = pa.ipc.serialize_record_batch(batch).to_buffer().to_pybytes()
    for ws in ws_clients.copy():
        if not ws.closed:
            await ws.send_bytes(serialized)
        else:
            ws_clients.discard(ws)

def start_background_webserver():
    async def init_app():
        app = web.Application()
        import os
        import jinja2
        template_path = os.path.join(os.path.dirname(__file__), "..", "resources")
        app['jinja_env'] = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
        app.router.add_get('/', index)
        app.router.add_get('/ws', websocket_handler)
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
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

def main():
    start_background_webserver()
    node = Node()

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] in ("voltage", "current", "power", "soc", "runtime"):
                latest_power_metrics[event["id"]] = event["value"][0].as_py()
                if web_loop is not None:
                    asyncio.run_coroutine_threadsafe(broadcast_power_metrics(), web_loop)
            elif event["id"] == "available_sounds":
                global latest_available_sounds
                latest_available_sounds = event["value"].to_pylist()
                if web_loop is not None:
                    asyncio.run_coroutine_threadsafe(broadcast_power_metrics(), web_loop)
            elif event["id"] == "volume":
                global latest_volume
                latest_volume = event["value"][0].as_py()
                if web_loop is not None:
                    asyncio.run_coroutine_threadsafe(broadcast_power_metrics(), web_loop)
            elif event["id"] == "tick":
                flush_web_inputs(node)


if __name__ == "__main__":
    main()
