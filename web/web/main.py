from dora import Node
import pyarrow as pa
import threading
import asyncio
import queue
from aiohttp import web


web_input_queue = queue.Queue()

def process_web_inputs(node):
    while True:
        try:
            web_event = web_input_queue.get_nowait()
        except queue.Empty:
            return
        print("Received web input:", web_event)
        if web_event.get("action") == "button":
            node.send_output(output_id="my_output_id", data=pa.array([4, 5, 6]), metadata={})
        elif web_event.get("action") == "slider":
            try:
                slider_value = int(web_event.get("value"))
                node.send_output(output_id="slider_input", data=pa.array([slider_value]), metadata={})
            except ValueError:
                print("Invalid slider value received:", web_event.get("value"))

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            try:
                # Expect messages in the format "button" or "slider:<value>"
                data = msg.data.strip().split(":")
                if data[0] == "button":
                    web_input_queue.put({"action": "button"})
                elif data[0] == "slider" and len(data) > 1:
                    web_input_queue.put({"action": "slider", "value": data[1]})
            except Exception as e:
                print("Error processing websocket message", e)
    return ws

async def index(request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Web Control</title>
    </head>
    <body>
        <h1>Web Control</h1>
        <button onclick="sendButton()">Press me</button>
        <br><br>
        <input type="range" min="0" max="100" value="50" id="slider" oninput="sendSlider(this.value)">
        <script>
            const ws = new WebSocket('ws://' + location.host + '/ws');
            ws.onopen = function() {
                console.log('WebSocket connection established');
            };
            function sendButton() {
                ws.send('button');
            }
            function sendSlider(value) {
                ws.send('slider:' + value);
            }
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

def start_background_webserver():
    async def init_app():
        app = web.Application()
        app.router.add_get('/', index)
        app.router.add_get('/ws', websocket_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

    def run_loop():
        loop = asyncio.new_event_loop()
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
            if event["id"] == "tick":
                # Process any web input events
                process_web_inputs(node)
                # node.send_output(
                #     output_id="my_output_id", data=pa.array([1, 2, 3]), metadata={}
                # )


if __name__ == "__main__":
    main()
