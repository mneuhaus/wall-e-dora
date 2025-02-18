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
      <p>Position: {{ currentServo?.position || 'N/A' }}</p>
      <p>Speed: {{ currentServo?.speed || 'N/A' }}</p>
      <p>Torque: {{ currentServo?.torque || 'N/A' }}</p>
    </div>
    <div style="margin-top: 1rem;">
      <button @click="wiggle">Wiggle Servo</button>
      <button @click="calibrate" style="margin-left: 0.5rem;">Calibrate Servo</button>
    </div>
    <div style="margin-top: 1rem;" v-if="currentServo?.min_pos !== undefined">
      <p>Calibration Range:</p>
      <p>Min Position: {{ currentServo?.min_pos || 'Not calibrated' }}</p>
      <p>Max Position: {{ currentServo?.max_pos || 'Not calibrated' }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import node from '../Node.js';

const route = useRoute();
const id = route.params.id;
const newId = ref('');
const servos = ref([]);

function changeId() {
  if (newId.value !== '') {
    node.emit('change_servo_id', [parseInt(id), parseInt(newId.value)]);
  }
}

const newSpeed = ref(100);

node.on('servo_status', (event) => {
  servos.value = event.value;
  if (currentServo.value?.speed) {
    newSpeed.value = currentServo.value.speed;
  }
});

const currentServo = computed(() => 
  servos.value.find(servo => servo.id === parseInt(id))
);

function updateSpeed() {
  const currentPosition = currentServo.value?.position || 0;
  node.emit('set_servo', [parseInt(id), parseInt(currentPosition), parseInt(newSpeed.value)]);
}

function wiggle() {
  node.emit('wiggle', [parseInt(id)]);
}

function calibrate() {
  node.emit('calibrate', [parseInt(id)]);
}
</script>

<style scoped>
.servo-debug {
  padding: 1rem;
}
</style>
