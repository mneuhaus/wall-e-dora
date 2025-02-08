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
        <!--Import Google Icon Font-->
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <!--Import materialize.css-->
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@materializecss/materialize@2.2.0/dist/css/materialize.min.css" media="screen,projection"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>Power Metrics</title>
      </head>
      <body>
        <nav>
          <div class="nav-wrapper teal">
            <a href="#!" class="brand-logo center">Power Metrics</a>
            <ul id="nav-mobile" class="right">
              <li><span id="status" class="new badge red" data-badge-caption="Offline"></span></li>
            </ul>
          </div>
        </nav>
        <div class="container">
          <div class="section">
            <h5>Metrics</h5>
            <table class="highlight">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Voltage</td>
                  <td id="voltage">-- V</td>
                </tr>
                <tr>
                  <td>Current</td>
                  <td id="current">-- A</td>
                </tr>
                <tr>
                  <td>Power</td>
                  <td id="power">-- W</td>
                </tr>
                <tr>
                  <td>SoC</td>
                  <td id="soc">-- %</td>
                </tr>
                <tr>
                  <td>Runtime</td>
                  <td id="runtime">-- s</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="section">
            <h5>Controls</h5>
            <a class="waves-effect waves-light btn" onclick="sendButton()">Press me</a>
            <br><br>
            <p class="range-field">
              <input type="range" id="slider" min="0" max="100" value="50" onchange="sendSlider(this.value)"/>
            </p>
          </div>
        </div>
        <!--Import jQuery before materialize.js-->
        <script src="https://code.jquery.com/jquery-3.2.1.min.js"></script>
        <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/@materializecss/materialize@2.2.0/dist/js/materialize.min.js"></script>
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
              var statusElem = document.getElementById('status');
              if (connected) {
                  statusElem.className = "new badge green";
                  statusElem.setAttribute("data-badge-caption", "Online");
              } else {
                  statusElem.className = "new badge red";
                  statusElem.setAttribute("data-badge-caption", "Offline");
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
                      var metrics = JSON.parse(event.data);
                      updateMetrics(metrics);
                  } catch(e) {
                      console.log("Failed to parse metrics:", e);
                  }
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
