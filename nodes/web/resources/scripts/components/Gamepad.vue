<template>
  <span :style="iconStyle">
    <i class="fa-solid fa-gamepad"></i>
  </span>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';

// Using the browser's gamepad API
const connected = ref(false);

function checkGamepad() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [];
  connected.value = pads && Array.from(pads).some(pad => pad);
}

// Check for gamepad connection at regular intervals.
let intervalId = null;
onMounted(() => {
  intervalId = setInterval(checkGamepad, 1000);
});
onUnmounted(() => {
  clearInterval(intervalId);
});

const iconStyle = computed(() => ({
  color: connected.value ? 'green' : 'gray',
  fontSize: '24px',
  marginLeft: '16px'
}));
</script>
