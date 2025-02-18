<template>
  <div class="servo-debug">
    <article class="responsive">
      <h5>Servo Debug - {{ id }}</h5>
      <p class="small">This is where you can inspect and test servo behavior.</p>

      <div class="field label border round">
        <input type="number" v-model="newId">
        <label>New Servo ID</label>
        <button class="small" @click="changeId">Change ID</button>
      </div>

      <div class="field label border round m-top">
        <label class="slider">
          <input type="range" min="100" max="2000" step="1" v-model="newSpeed" @change="updateSpeed">
          <span>Speed: {{ newSpeed }}</span>
        </label>
      </div>

      <div class="card m-top">
        <div class="row">
          <div class="col s12">
            <h6>Current Status</h6>
            <table class="small border">
              <tbody>
                <tr>
                  <td>Position:</td>
                  <td>{{ currentServo?.position || 'N/A' }}</td>
                </tr>
                <tr>
                  <td>Speed:</td>
                  <td>{{ currentServo?.speed || 'N/A' }}</td>
                </tr>
                <tr>
                  <td>Torque:</td>
                  <td>{{ currentServo?.torque || 'N/A' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="card m-top">
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
              :start-angle="0"
              :end-angle="360"
              :animation="false"
              @update="handlePositionUpdate"
            />
          </div>
        </div>
      </div>

      <div class="row m-top">
        <button class="border" @click="wiggle">
          <i class="fa-solid fa-arrows-left-right"></i>
          Wiggle
        </button>
        <button class="border" @click="calibrate">
          <i class="fa-solid fa-ruler"></i>
          Calibrate
        </button>
      </div>

      <div class="card m-top" v-if="currentServo?.min_pos !== undefined">
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
      </div>
    </article>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import node from '../Node.js';
import RoundSlider from 'vue-round-slider';

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
const currentPosition = ref(0);
const minPos = computed(() => currentServo.value?.min_pos || 0);
const maxPos = computed(() => currentServo.value?.max_pos || 1024);

node.on('servo_status', (event) => {
  servos.value = event.value;
  if (currentServo.value?.speed) {
    newSpeed.value = currentServo.value.speed;
  }
  if (currentServo.value?.position) {
    currentPosition.value = currentServo.value.position;
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

function handlePositionUpdate(newValue) {
  node.emit('set_servo', [parseInt(id), parseInt(newValue), parseInt(newSpeed.value)]);
}
</script>

<style scoped>
.servo-debug {
  padding: 1rem;
}
</style>
