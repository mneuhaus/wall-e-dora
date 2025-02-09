<template>
  <!-- This component does not render any visible UI -->
  <div style="display: none;"></div>
</template>

<script>
export default {
  name: "NodeComponent",
  data() {
    return {
      eventQueue: [],
      outputQueue: [],
      ws: null,
    };
  },
  created() {
    console.log("JS Node initialized - Vue Component");
    this.connectWebSocket();
    this.processEventQueue();
  },
  methods: {
    processEventQueue() {
      setInterval(() => {
        while (this.eventQueue.length > 0) {
          const event = this.eventQueue.shift();
          this.$emit('message', event);
        }
      }, 100);
    },
    sendOutput(output_id, data, metadata = {}) {
      const message = { output_id, data, metadata };
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log(message);
        this.ws.send(JSON.stringify(message));
      } else {
        console.log("JS Node sending output:", message);
        this.outputQueue.push(message);
      }
    },
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
};
</script>
