<template>
  <div class="servo-status">
    <label for="servoDropdown">Servos:</label>
    <select id="servoDropdown" @change="handleSelect">
      <option value="" disabled selected>Select Servo</option>
      <option v-for="servo in servos" :key="servo.id" :value="servo.id">
        Servo {{ servo.id }} (Pos: {{ servo.position }})
      </option>
    </select>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import node from '../Node.js';
import { useRouter } from 'vue-router';

const servos = ref([]);
const router = useRouter();

node.on('servo_status', (event) => {
  servos.value = event.value;
});

function handleSelect(event) {
  const selected = event.target.value;
  if (selected) {
    router.push({ name: 'servo', params: { id: selected } });
  }
}
</script>

<style scoped>
.servo-status {
  margin-left: 1rem;
}
</style>
