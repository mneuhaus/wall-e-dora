<template>
  <div class="servo-debug">
    <h2>Servo Debug - {{ id }}</h2>
    <p>This is where you can inspect and test servo behavior.</p>
    <div style="margin-top: 1rem;">
      <label for="newServoId">New Servo ID:</label>
      <input id="newServoId" type="number" v-model="newId" style="width: 60px; margin-left: 0.5rem;" />
      <button @click="changeId" style="margin-left: 0.5rem;">Change Servo ID</button>
    </div>
    <div style="margin-top: 1rem;">
      <label for="newSpeed">Servo Speed:</label>
      <input id="newSpeed" type="range" min="100" max="2000" step="1" v-model="newSpeed" @change="updateSpeed" style="width: 300px; margin-left: 0.5rem;" />
      <span>{{ newSpeed }}</span>
    </div>
    <div style="margin-top: 1rem;">
      <p>Current Servo Status:</p>
      <p>Position: {{ servoStatus.position }}</p>
      <p>Speed: {{ servoStatus.speed }}</p>
      <p>Torque: {{ servoStatus.torque }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRoute } from 'vue-router';
import node from '../Node.js';
const route = useRoute();
const id = route.params.id;
const newId = ref('');
function changeId() {
  if (newId.value !== '') {
    node.emit('change_servo_id', [parseInt(id), parseInt(newId.value)]);
  }
}

const newSpeed = ref(100);
const servoStatus = ref({});
node.on('servo_status', (event) => {
  servoStatus.value = event.value;
  if (event.value.speed) {
    newSpeed.value = event.value.speed;
  }
});
function updateSpeed() {
  const currentPosition = servoStatus.value.position || 0;
  node.emit('set_servo', [parseInt(id), parseInt(currentPosition), parseInt(newSpeed.value)]);
}
</script>

<style scoped>
.servo-debug {
  padding: 1rem;
}
</style>
