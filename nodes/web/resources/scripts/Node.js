import mitt from 'mitt';

class Node {
  constructor() {
    this.emitter = mitt();
    this.state = {
      eventQueue: [],
      outputQueue: [],
      ws: null,
    };
    this.connectWebSocket();
    this.processEventQueue();
    console.log("JS Node initialized - Vanilla JS (class based)");
  }

  processEventQueue() {
    setInterval(() => {
      while (this.state.eventQueue.length > 0) {
        const event = this.state.eventQueue.shift();
        // Use event.id as the event name if available; otherwise fallback to 'message'
        this.emitter.emit(event.id || 'message', event);
      }
    }, 100);
  }

  sendOutput(output_id, data, metadata = {}) {
    const message = { output_id, data, metadata };
    if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
      console.log(message);
      this.state.ws.send(JSON.stringify(message));
    } else {
      console.log("JS Node sending output:", message);
      this.state.outputQueue.push(message);
    }
  }

  connectWebSocket() {
    this.state.ws = new WebSocket('ws://' + location.host + '/ws');
    this.state.ws.binaryType = 'arraybuffer';
    this.state.ws.onopen = () => {
      console.log("WebSocket connection opened");
    };
    this.state.ws.onclose = () => {
      console.log("WebSocket connection closed, retrying in 1s");
      setTimeout(() => this.connectWebSocket(), 1000);
    };
    this.state.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.state.ws.close();
    };
    this.state.ws.addEventListener('message', (event) => {
      try {
        let rawData = event.data;
        if (typeof rawData !== "string") {
          rawData = new TextDecoder("utf-8").decode(new Uint8Array(rawData));
        }
        const data = JSON.parse(rawData);
        this.state.eventQueue.push(data);
      } catch (e) {
        console.log("Failed to parse message:", e);
      }
    });
  }

  on(eventName, callback) {
    this.emitter.on(eventName, callback);
  }

  emit(output_id, data, metadata = {}) {
    this.sendOutput(output_id, data, metadata);
  }
}

let node = new Node();

export default node;