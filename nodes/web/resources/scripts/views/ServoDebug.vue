<template>
  <div class="servo-debug">
    <article class="responsive">
      <!-- Header Section -->
      <header>
        <h5>Servo Debug - {{ id }}</h5>
        <p class="small">This is where you can inspect and test servo behavior.</p>
      </header>

      <!-- ID Configuration Section -->
      <section class="field label border round">
        <input type="number" v-model="newId">
        <label>New Servo ID</label>
        <button class="small" @click="changeId">Change ID</button>
      </section>

      <!-- Speed Control Section -->
      <section class="field label border round m-top">
        <label class="slider">
          <input type="range" min="100" max="2000" step="1" v-model="newSpeed" @change="updateSpeed">
          <span>Speed: {{ newSpeed }}</span>
        </label>
      </section>

      <!-- Status Display Section -->
      <section class="card m-top">
        <div class="row">
          <div class="col s12">
            <h6>Current Status</h6>
            <table class="small border">
              <tbody>
                <tr v-for="(value, key) in servoStatus" :key="key">
                  <td>{{ key }}:</td>
                  <td>{{ value }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- Position Control Section -->
      <section class="card m-top">
        <div class="row">
          <div class="col s12 center-align">
            <round-slider
              v-model="currentPosition"
              :min="minPos"
              :max="maxPos"
              radius="120"
              line-cap="round"
              path-color="#37474F"
              range-color="#00bfa5"
              :start-angle="300"
              :end-angle="600"
              :animation="false"
            />
          </div>
        </div>
      </section>

      <!-- Action Buttons Section -->
      <section class="row m-top">
        <button class="border" @click="wiggle">
          <i class="fa-solid fa-arrows-left-right"></i>
          Wiggle
        </button>
        <button class="border" @click="calibrate">
          <i class="fa-solid fa-ruler"></i>
          Calibrate
        </button>
      </section>

      <!-- Calibration Info Section -->
      <section class="card m-top" v-if="currentServo?.min_pos !== undefined">
        <div class="row">
          <div class="col s12">
            <h6>Calibration Range</h6>
            <table class="small border">
              <tbody>
                <tr>
                  <td>Min Position:</td>
                  <td>{{ currentServo?.min_pos || 'Not calibrated' }}</td>
                </tr>
                <tr>
                  <td>Max Position:</td>
                  <td>{{ currentServo?.max_pos || 'Not calibrated' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </article>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import node from '../Node.js';
import RoundSlider from 'vue-three-round-slider';

// Route and basic setup
const route = useRoute();
const id = route.params.id;
const servos = ref([]);

// Form controls
const newId = ref('');
const newSpeed = ref(100);
const currentPosition = ref(0);

// Computed properties
const currentServo = computed(() => 
  servos.value.find(servo => servo.id === parseInt(id))
);

const minPos = computed(() => currentServo.value?.min_pos || 0);
const maxPos = computed(() => currentServo.value?.max_pos || 1024);

const servoStatus = computed(() => ({
  Position: currentServo.value?.position || 'N/A',
  Speed: currentServo.value?.speed || 'N/A',
  Torque: currentServo.value?.torque || 'N/A'
}));

// Event handlers
node.on('servo_status', (event) => {
  servos.value = event.value;
  console.log(event.value);
  if (currentServo.value?.speed) {
    newSpeed.value = currentServo.value.speed;
  }
  if (currentServo.value?.position) {
    currentPosition.value = currentServo.value.position;
  }
});

// Action methods
function changeId() {
  if (newId.value !== '') {
    node.emit('change_servo_id', [parseInt(id), parseInt(newId.value)]);
  }
}

function updateSpeed() {
  if (!currentServo.value) return;
  node.emit('set_servo', [parseInt(id), parseInt(currentPosition.value), parseInt(newSpeed.value)]);
}

function wiggle() {
  node.emit('wiggle', [parseInt(id)]);
}

function calibrate() {
  node.emit('calibrate', [parseInt(id)]);
}

// Watch for position changes
watch(currentPosition, (newValue) => {
  node.emit('set_servo', [parseInt(id), parseInt(newValue), parseInt(newSpeed.value)]);
});
</script>

<style scoped>
.servo-debug {
  padding: 1rem;
}
</style>
