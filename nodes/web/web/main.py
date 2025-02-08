from dora import Node
import pyarrow as pa
import threading
import asyncio
import queue
from aiohttp import web


global_web_inputs = []
latest_power_metrics = {}
ws_clients = set()
web_loop = None

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
        elif web_event.get("action") == "sound_click":
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
                    # Expect messages in the format "button" or "slider:<value>"
                    data = msg.data.strip().split(":")
                    if data[0] == "button":
                        global_web_inputs.append({"action": "button"})
                    elif data[0] == "slider" and len(data) > 1:
                        global_web_inputs.append({"action": "slider", "value": data[1]})
                except Exception as e:
                    print("Error processing websocket message", e)
    finally:
        ws_clients.discard(ws)
    return ws

async def index(request):
    html_content = """
    <!DOCTYPE html>
    <html>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
        <script type="importmap">
          {
            "imports": {
              "@material/web/": "https://esm.run/@material/web/"
            }
          }
        </script>
        <script type="module">
          import '@material/web/all.js';
          import {styles as typescaleStyles} from '@material/web/typography/md-typescale-styles.js';
          document.adoptedStyleSheets.push(typescaleStyles.styleSheet);
        </script>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>Power Metrics</title>
        <style>
          body { margin:0; font-family: Roboto, sans-serif; }
          .status-bar { display: flex; align-items: center; justify-content: space-between; background-color: #6200ee; color: white; padding: 10px 16px; }
          .status-indicator { display: flex; align-items: center; }
          .status-indicator span { margin-left: 8px; }
          .metrics-table { margin: 16px 0; }
          table { width: 100%; border-collapse: collapse; }
          th, td { padding: 8px 12px; border-bottom: 1px solid #ddd; }
          .controls { margin: 16px 0; }
        </style>
      </head>
      <body>
        <header class="status-bar">
          <div class="status-indicator">
            <md-icon style="color: white;">power</md-icon>
            <span>Power Metrics</span>
          </div>
          <div id="connection-status">
            <md-icon id="status-icon" style="color: red;">cloud_off</md-icon>
          </div>
        </header>
        <main class="container" style="padding: 16px;">
          <section class="metrics-table">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>Voltage</td><td id="voltage">-- V</td></tr>
                <tr><td>Current</td><td id="current">-- A</td></tr>
                <tr><td>Power</td><td id="power">-- W</td></tr>
                <tr><td>SoC</td><td id="soc">-- %</td></tr>
                <tr><td>Runtime</td><td id="runtime">-- s</td></tr>
              </tbody>
            </table>
          </section>
          <section class="controls">
            <md-outlined-button onclick="sendButton()">Press me</md-outlined-button>
            <div style="margin-top: 16px;">
              <label for="slider">Adjust value:</label>
              <md-slider id="slider" min="0" max="100" value="50" discrete onchange="sendSlider(this.value)"></md-slider>
            </div>
          </section>
          <section id="sound-list">
            <h2>Available Sounds</h2>
            <ul id="sounds"></ul>
          </section>
        </main>
        <script>
          var ws;
          function updateMetrics(metrics) {
            document.getElementById('voltage').innerText = metrics.voltage + " V";
            document.getElementById('current').innerText = metrics.current + " A";
            document.getElementById('power').innerText = metrics.power + " W";
            document.getElementById('soc').innerText = metrics.soc + " %";
            document.getElementById('runtime').innerText = metrics.runtime + " s";
          }
          function updateStatus(connected) {
            var statusIcon = document.getElementById('status-icon');
            if (connected) {
              statusIcon.innerText = "cloud";
              statusIcon.style.color = "green";
            } else {
              statusIcon.innerText = "cloud_off";
              statusIcon.style.color = "red";
            }
          }
          function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws');
            ws.onopen = function() {
              updateStatus(true);
            };
            ws.onclose = function() {
              updateStatus(false);
              setTimeout(connect, 1000);
            };
            ws.onerror = function(error) {
              ws.close();
            };
            ws.onmessage = function(event) {
              try {
                var data = JSON.parse(event.data);
                if (data.hasOwnProperty("available_sounds")) {
                  updateSoundList(data.available_sounds);
                }
                if (data.hasOwnProperty("voltage")) {
                  updateMetrics(data);
                }
              } catch(e) {
                console.log("Failed to parse metrics:", e);
              }
            };
            function updateSoundList(sounds) {
              var soundsList = document.getElementById('sounds');
              soundsList.innerHTML = '';
              sounds.forEach(function(sound) {
                var li = document.createElement('li');
                li.innerText = sound;
                li.style.cursor = 'pointer';
                li.onclick = function() { sendSound(sound); };
                soundsList.appendChild(li);
              });
            }
            function sendSound(sound) {
              if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send('sound_click:' + sound);
              }
            }
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

async def broadcast_power_metrics():
    safe_metrics = {}
    for key, value in latest_power_metrics.items():
        if isinstance(value, float) and (value == float("inf") or value != value):
            safe_metrics[key] = "Infinity"
        else:
            safe_metrics[key] = value
    for ws in ws_clients.copy():
        if not ws.closed:
            await ws.send_json(safe_metrics)
        else:
            ws_clients.discard(ws)

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
            elif event["id"] == "tick":
                flush_web_inputs(node)


if __name__ == "__main__":
    main()
