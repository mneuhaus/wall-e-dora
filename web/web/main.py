from dora import Node
import pyarrow as pa
import threading
import asyncio
import queue
from aiohttp import web


global_web_inputs = []

def flush_web_inputs(node):
    global global_web_inputs
    if not global_web_inputs:
        return
    for web_event in global_web_inputs:
        print("Processing web input:", web_event)
        if web_event.get("action") == "button":
            node.send_output(output_id="my_output_id", data=pa.array([4, 5, 6]), metadata={})
        elif web_event.get("action") == "slider":
            try:
                slider_value = int(web_event.get("value"))
                node.send_output(output_id="slider_input", data=pa.array([slider_value]), metadata={})
            except ValueError:
                print("Invalid slider value received:", web_event.get("value"))
    global_web_inputs = []

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            try:
                # Expect messages in the format "button" or "slider:<value>"
                data = msg.data.strip().split(":")
                if data[0] == "button":
                    global_web_inputs.append({"action": "button"})
                elif data[0] == "slider" and len(data) > 1:
                    global_web_inputs.append({"action": "slider", "value": data[1]})
            except Exception as e:
                print("Error processing websocket message", e)
    return ws

async def index(request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Web Control</title>
        <style>
            #status {
                width: 20px;
                height: 20px;
                display: inline-block;
                border: 1px solid #000;
                border-radius: 50%;
                margin-left: 10px;
            }
        </style>
    </head>
    <body>
        <h1>Web Control <span id="status" style="background-color: red;"></span></h1>
        <button onclick="sendButton()">Press me</button>
        <br><br>
        <input type="range" min="0" max="100" value="50" id="slider" oninput="sendSlider(this.value)">
        <script>
            var ws;
            function connect() {
                ws = new WebSocket('ws://' + location.host + '/ws');
                ws.onopen = function() {
                    console.log('WebSocket connection established');
                    document.getElementById('status').style.backgroundColor = 'green';
                };
                ws.onclose = function() {
                    console.log('WebSocket connection closed, retrying...');
                    document.getElementById('status').style.backgroundColor = 'red';
                    setTimeout(connect, 1000);
                };
                ws.onerror = function(error) {
                    console.log('WebSocket error:', error);
                    ws.close();
                };
                ws.onmessage = function(event) {
                    console.log('Message from server:', event.data);
                };
            }
            connect();
            function sendButton() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('button');
                }
            }
            function sendSlider(value) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('slider:' + value);
                }
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
                flush_web_inputs(node)


if __name__ == "__main__":
    main()
