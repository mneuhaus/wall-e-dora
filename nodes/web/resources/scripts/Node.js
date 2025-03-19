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
    console.log("JS Node initialized - Vanilla JS (class based)");
  }

  processEventQueue() {
    setInterval(() => {
      while (this.state.eventQueue.length > 0) {
        const event = this.state.eventQueue.shift();
        // Log only for servo-related events
        if (event.id === 'servo_status') {
          console.log("[DEBUG] Received servo_status event:", 
            event.value ? `${event.value.length} servos` : "no servos");
        }
        // Use event.id as the event name if available; otherwise fallback to 'message'
        this.emitter.emit(event.id || 'message', event);
      }
    }, 100);
  }

  sendOutput(output_id, data, metadata = {}) {
    const message = { output_id, data, metadata };
    if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
      // Log only for servo-related outputs
      if (output_id === 'SCAN' || output_id === 'set_servo') {
        console.log(`[DEBUG] Sending ${output_id}:`, data);
      }
      this.state.ws.send(JSON.stringify(message));
    } else {
      if (output_id === 'SCAN' || output_id === 'set_servo') {
        console.log(`[DEBUG] Queuing ${output_id} (WebSocket not ready):`, data);
      }
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
    
    console.log(`WebSocket connecting (attempt ${this.state.reconnectAttempts + 1})...`);
    
    // Get the correct host and port
    const host = location.host || 'localhost:8443';
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${host}/ws`;
    
    console.log(`Connecting to WebSocket at ${wsUrl}`);
    
    this.state.ws = new WebSocket(wsUrl);
    this.state.ws.binaryType = 'arraybuffer';
    
    this.state.ws.onopen = () => {
      console.log("WebSocket connection opened successfully");
      this.emitter.emit('connection', true);
      this.state.reconnectAttempts = 0;
      this.state.reconnectInterval = 1000;
      
      // Send any queued messages
      while (this.state.outputQueue.length > 0) {
        const message = this.state.outputQueue.shift();
        console.log("Sending queued message:", message);
        this.state.ws.send(JSON.stringify(message));
      }
      
      // Request servo data on successful connection
      this.sendOutput('SCAN', []);
    };
    
    this.state.ws.onclose = (event) => {
      console.log(`WebSocket connection closed (code: ${event.code}, reason: ${event.reason})`);
      this.emitter.emit('connection', false);
      
      // Implement exponential backoff for reconnection attempts
      this.state.reconnectAttempts++;
      
      if (this.state.reconnectAttempts < this.state.maxReconnectAttempts) {
        const delay = Math.min(30000, this.state.reconnectInterval * Math.pow(1.5, this.state.reconnectAttempts - 1));
        console.log(`Reconnecting in ${delay}ms (attempt ${this.state.reconnectAttempts})`);
        setTimeout(() => this.connectWebSocket(), delay);
      } else {
        console.error(`Failed to reconnect after ${this.state.maxReconnectAttempts} attempts`);
      }
    };
    
    this.state.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      // No need to call close, the onclose handler will be called automatically
    };
    
    this.state.ws.addEventListener('message', (event) => {
      try {
        let rawData = event.data;
        if (typeof rawData !== "string") {
          rawData = new TextDecoder("utf-8").decode(new Uint8Array(rawData));
        }
        
        console.log("Received WebSocket message:", rawData);
        const data = JSON.parse(rawData);
        this.state.eventQueue.push(data);
      } catch (e) {
        console.error("Failed to parse message:", e, event.data);
      }
    });
  }

  on(eventName, callback) {
    // Only log for servo-related events
    if (eventName === 'servo_status') {
      console.log(`[DEBUG] Registering listener for: ${eventName}`);
    }
    this.emitter.on(eventName, callback);
    return () => this.emitter.off(eventName, callback); // Return unsubscribe function for React useEffect
  }

  emit(output_id, data, metadata = {}) {
    // Only log for servo-related events
    if (output_id === 'SCAN' || output_id === 'set_servo') {
      console.log(`[DEBUG] Emitting ${output_id}:`, data);
    }
    this.sendOutput(output_id, data, metadata);
  }
}

let node = new Node();

// For debugging
window.debugNode = node;

export default node;