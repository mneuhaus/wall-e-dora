class Node {
  constructor() {
    this.eventQueue = [];
    this.outputQueue = [];
    // Initialization logic: connect to backend if needed
    console.log("JS Node initialized");
    this.connectWebSocket();
  }

  // Simulate receiving the next event from the DORA stack
  next() {
    return new Promise(resolve => {
      const checkQueue = () => {
        if (this.eventQueue.length > 0) {
          resolve(this.eventQueue.shift());
        } else {
          setTimeout(checkQueue, 100);
        }
      };
      checkQueue();
    });
  }

  // Send output message to DORA stack
  send_output(output_id, data, metadata = {}) {
    const message = { output_id, data, metadata };
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.log("JS Node sending output:", message);
      this.outputQueue.push(message);
    }
  }

  setWebsocket(ws) {
    this.ws = ws;
    while (this.outputQueue.length > 0 && this.ws.readyState === WebSocket.OPEN) {
      let msg = this.outputQueue.shift();
      this.ws.send(JSON.stringify(msg));
    }
  }

  connectWebSocket() {
    this.ws = new WebSocket('ws://' + location.host + '/ws');
    this.ws.binaryType = 'arraybuffer';
    this.ws.onopen = () => {
      console.log("WebSocket connection opened");
      this.setWebsocket(this.ws);
      console.debug("WebSocket debug: connected to", this.ws.url);
    };
    this.ws.onclose = () => {
      console.log("WebSocket connection closed, retrying in 1s");
      setTimeout(() => this.connectWebSocket(), 1000);
    };
    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.ws.close();
    };
    this.ws.onmessage = (event) => {
      console.debug("WebSocket message received:", event);
      try {
        let rawData = event.data;
        if (typeof rawData !== "string") {
          rawData = new TextDecoder("utf-8").decode(new Uint8Array(rawData));
        }
        const data = JSON.parse(rawData);
        console.debug("Parsed message:", data);
        this.push_event(data);
      } catch (e) {
        console.log("Failed to parse message:", e);
      }
    };
  }

  // For testing: method to simulate receiving an event
  push_event(event) {
    this.eventQueue.push(event);
  }
}

export { Node };
