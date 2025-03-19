import mitt from 'mitt';

class Node {
  constructor() {
    this.emitter = mitt();
    this.state = {
      eventQueue: [],
      outputQueue: [],
      ws: null,
      reconnectAttempts: 0,
      maxReconnectAttempts: 10,
      reconnectInterval: 1000, // Start with 1s, will increase
    };
    this.connectWebSocket();
    this.processEventQueue();
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
      this.state.ws.send(JSON.stringify(message));
    } else {
      this.state.outputQueue.push(message);
      // Try to reconnect if not already in process
      if (!this.state.ws || this.state.ws.readyState === WebSocket.CLOSED) {
        this.connectWebSocket();
      }
    }
  }

  connectWebSocket() {
    // If we already have a connection or are connecting, don't try to connect again
    if (this.state.ws && (this.state.ws.readyState === WebSocket.CONNECTING || this.state.ws.readyState === WebSocket.OPEN)) {
      return;
    }
    
    // Get the correct host and port
    const host = location.host || 'localhost:8443';
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${host}/ws`;
    
    this.state.ws = new WebSocket(wsUrl);
    this.state.ws.binaryType = 'arraybuffer';
    
    this.state.ws.onopen = () => {
      this.emitter.emit('connection', true);
      this.state.reconnectAttempts = 0;
      this.state.reconnectInterval = 1000;
      
      // Send any queued messages
      while (this.state.outputQueue.length > 0) {
        const message = this.state.outputQueue.shift();
        this.state.ws.send(JSON.stringify(message));
      }
      
      // Request servo data on successful connection
      this.sendOutput('SCAN', []);
    };
    
    this.state.ws.onclose = (event) => {
      this.emitter.emit('connection', false);
      
      // Implement exponential backoff for reconnection attempts
      this.state.reconnectAttempts++;
      
      if (this.state.reconnectAttempts < this.state.maxReconnectAttempts) {
        const delay = Math.min(30000, this.state.reconnectInterval * Math.pow(1.5, this.state.reconnectAttempts - 1));
        setTimeout(() => this.connectWebSocket(), delay);
      }
    };
    
    this.state.ws.onerror = (error) => {
      // No need to call close, the onclose handler will be called automatically
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
        // Silent error handling for parse issues
      }
    });
  }

  on(eventName, callback) {
    this.emitter.on(eventName, callback);
    return () => this.emitter.off(eventName, callback); // Return unsubscribe function for React useEffect
  }

  emit(output_id, data, metadata = {}) {
    this.sendOutput(output_id, data, metadata);
  }
}

let node = new Node();

// Make node available globally for advanced usage scenarios
window.node = node;

export default node;