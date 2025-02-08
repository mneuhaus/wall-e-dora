class Node {
  constructor() {
    this.eventQueue = [];
    this.outputQueue = [];
    // Initialization logic: connect to backend if needed
    console.log("JS Node initialized");
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

  // For testing: method to simulate receiving an event
  push_event(event) {
    this.eventQueue.push(event);
  }
}

export { Node };
