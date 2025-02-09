<template>
  <!-- This component does not render any visible UI -->
  <div style="display: none;"></div>
</template>

<script setup>
import { reactive, onMounted } from 'vue';

const state = reactive({
  eventQueue: [],
  outputQueue: [],
  ws: null,
});

const emit = defineEmits(['message']);

function processEventQueue() {
  setInterval(() => {
    while (state.eventQueue.length > 0) {
      const event = state.eventQueue.shift();
      emit('message', event);
    }
  }, 100);
}

function sendOutput(output_id, data, metadata = {}) {
  const message = { output_id, data, metadata };
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    console.log(message);
    state.ws.send(JSON.stringify(message));
  } else {
    console.log("JS Node sending output:", message);
    state.outputQueue.push(message);
  }
}

function connectWebSocket() {
  state.ws = new WebSocket('ws://' + location.host + '/ws');
  state.ws.binaryType = 'arraybuffer';
  state.ws.onopen = () => {
    console.log("WebSocket connection opened");
  };
  state.ws.onclose = () => {
    console.log("WebSocket connection closed, retrying in 1s");
    setTimeout(() => connectWebSocket(), 1000);
  };
  state.ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    state.ws.close();
  };
  state.ws.addEventListener('message', (event) => {
    try {
      let rawData = event.data;
      if (typeof rawData !== "string") {
        rawData = new TextDecoder("utf-8").decode(new Uint8Array(rawData));
      }
      const data = JSON.parse(rawData);
      state.eventQueue.push(data);
    } catch (e) {
      console.log("Failed to parse message:", e);
    }
  });
}

onMounted(() => {
  console.log("JS Node initialized - Vue Component (Composition API)");
  connectWebSocket();
  processEventQueue();
});
</script>
