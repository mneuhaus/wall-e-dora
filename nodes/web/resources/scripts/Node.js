import mitt from 'mitt';

const NON_ACTIVITY_OUTPUTS = new Set([
  'SCAN',
  'scan_sounds',
  'list_images',
  'list_gamepad_profiles',
  'get_gamepad_profile',
  'check_gamepad_profile',
]);

class Node {
  constructor() {
    this.emitter = mitt();
    this.state = {
      eventQueue: [],
      outputQueue: [],
      lastEvents: {},
      ws: null,
      reconnectAttempts: 0,
      maxReconnectAttempts: 10,
      reconnectInterval: 1000,
      lastUserInteractionAt: Date.now(),
      lastUserInteraction: null,
    };
    this.connectWebSocket();
    this.processEventQueue();
  }

  processEventQueue() {
    setInterval(() => {
      while (this.state.eventQueue.length > 0) {
        const event = this.state.eventQueue.shift();
        this.emitter.emit(event.id || 'message', event);
      }
    }, 100);
  }

  shouldTrackActivity(outputId, options = {}) {
    if (options.trackActivity === false) {
      return false;
    }
    return !NON_ACTIVITY_OUTPUTS.has(outputId);
  }

  recordUserActivity(outputId) {
    const activity = {
      output_id: outputId,
      at: Date.now(),
    };
    this.state.lastUserInteractionAt = activity.at;
    this.state.lastUserInteraction = activity;
    this.emitter.emit('user_activity', activity);
  }

  sendOutput(output_id, data, metadata = {}, options = {}) {
    if (this.shouldTrackActivity(output_id, options)) {
      this.recordUserActivity(output_id);
    }

    const message = { output_id, data, metadata };
    if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
      this.state.ws.send(JSON.stringify(message));
    } else {
      this.state.outputQueue.push(message);
      if (!this.state.ws || this.state.ws.readyState === WebSocket.CLOSED) {
        this.connectWebSocket();
      }
    }
  }

  connectWebSocket() {
    if (
      this.state.ws
      && (
        this.state.ws.readyState === WebSocket.CONNECTING
        || this.state.ws.readyState === WebSocket.OPEN
      )
    ) {
      return;
    }

    const host = location.host || 'localhost:8443';
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${host}/ws`;

    this.state.ws = new WebSocket(wsUrl);
    this.state.ws.binaryType = 'arraybuffer';

    this.state.ws.onopen = () => {
      this.emitter.emit('connection', true);
      this.state.reconnectAttempts = 0;
      this.state.reconnectInterval = 1000;

      while (this.state.outputQueue.length > 0) {
        const message = this.state.outputQueue.shift();
        this.state.ws.send(JSON.stringify(message));
      }

      this.sendOutput('SCAN', [], {}, { trackActivity: false });
    };

    this.state.ws.onclose = () => {
      this.emitter.emit('connection', false);
      this.state.reconnectAttempts += 1;

      if (this.state.reconnectAttempts < this.state.maxReconnectAttempts) {
        const delay = Math.min(
          30000,
          this.state.reconnectInterval * Math.pow(1.5, this.state.reconnectAttempts - 1),
        );
        setTimeout(() => this.connectWebSocket(), delay);
      }
    };

    this.state.ws.onerror = () => {
      // onclose handles reconnection.
    };

    this.state.ws.addEventListener('message', (event) => {
      try {
        let rawData = event.data;
        if (typeof rawData !== 'string') {
          rawData = new TextDecoder('utf-8').decode(new Uint8Array(rawData));
        }

        const data = JSON.parse(rawData);
        if (data && data.id) {
          this.state.lastEvents[data.id] = data;
        }
        this.state.eventQueue.push(data);
      } catch (error) {
        // Silent parse failure to keep the UI responsive.
      }
    });
  }

  on(eventName, callback) {
    this.emitter.on(eventName, callback);
    return () => this.emitter.off(eventName, callback);
  }

  getLastEvent(eventName) {
    return this.state.lastEvents[eventName] || null;
  }

  getLastUserInteractionAt() {
    return this.state.lastUserInteractionAt;
  }

  getLastUserInteraction() {
    return this.state.lastUserInteraction;
  }

  emit(output_id, data, metadata = {}, options = {}) {
    this.sendOutput(output_id, data, metadata, options);
  }
}

let node = new Node();

window.node = node;

export default node;
