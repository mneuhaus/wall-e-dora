<template>
  <span :style="iconStyle" @click="toggleModal">
    <i class="fa-solid fa-gamepad" style="width: 30px;"></i>
  </span>
  <div v-if="showModal" class="gamepad-debug-modal">
    <GamepadDebug />
    <button @click="closeModal" style="position: absolute; top: 10px; right: 10px; z-index: 1001;">Close</button>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import GamepadDebug from './GamepadDebug.vue';

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

const showModal = ref(false);
const debugData = ref({});

function toggleModal() {
  showModal.value = !showModal.value;
}

function closeModal() {
  showModal.value = false;
}

function updateDebugData() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [];
  const currentPad = pads && pads[0] ? pads[0] : null;
  if (currentPad) {
    const currentData = {
      id: currentPad.id,
      buttons: currentPad.buttons.map(button => ({ pressed: button.pressed, value: button.value })),
      axes: currentPad.axes
    };
    console.log("Gamepad Input:", currentData);
    debugData.value = currentData;
  } else {
    debugData.value = {};
  }
}

let debugInterval = null;
onMounted(() => {
  // Existing interval for checking connection is set already.
  debugInterval = setInterval(updateDebugData, 100);
});
onUnmounted(() => {
  clearInterval(debugInterval);
});
</script>
<style scoped>
.gamepad-debug-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: 4px;
  max-width: 600px;
  width: 90%;
}
</style>
