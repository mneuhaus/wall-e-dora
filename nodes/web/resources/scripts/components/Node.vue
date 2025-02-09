class Node {
  constructor() {
    this.eventQueue = [];
    this.outputQueue = [];
    // Initialization logic: connect to backend if needed
    console.log("JS Node initialized");
    this.connectWebSocket();
  }

  // Simulate receiving the next event from the DORA stack
  next(callback) {
    const checkQueue = () => {
      while (this.eventQueue.length > 0) {
        let event = this.eventQueue.shift();
        callback(event);
      }
      setTimeout(checkQueue, 100);
    };
    checkQueue();
  }

  // Send output message to DORA stack
  send_output(output_id, data, metadata = {}) {
    const message = { output_id: output_id, data: data, metadata: metadata };
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log(message);
      this.ws.send(JSON.stringify(message));
    } else {
      console.log("JS Node sending output:", message);
      this.outputQueue.push(message);
    }
  }

  connectWebSocket() {
    this.ws = new WebSocket('ws://' + location.host + '/ws');
    this.ws.binaryType = 'arraybuffer';
    this.ws.onopen = () => {
      console.log("WebSocket connection opened");
    };
    this.ws.onclose = () => {
      console.log("WebSocket connection closed, retrying in 1s");
      setTimeout(() => this.connectWebSocket(), 1000);
    };
    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.ws.close();
    };
    this.ws.addEventListener('message', (event) => {
      // console.log("WebSocket message received via addEventListener:", event);
      try {
        let rawData = event.data;
        if (typeof rawData !== "string") {
          rawData = new TextDecoder("utf-8").decode(new Uint8Array(rawData));
        }
        const data = JSON.parse(rawData);
        this.eventQueue.push(data);
      } catch (e) {
        console.log("Failed to parse message:", e);
      }
    });
  }
}

export { Node };
