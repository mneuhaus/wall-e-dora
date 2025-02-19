<template>
  <div class="servo-debug">
    <article class="responsive">
      <!-- Header Section with Breadcrumb -->
      <header class="m-bottom-2">
        <nav aria-label="breadcrumb">
          <RouterLink to="/" class="small">Home</RouterLink>
          <span class="small">/</span>
          <span class="small" aria-current="page">Servo {{ id }}</span>
        </nav>
        <h5 class="m-top-1">Servo Control Panel</h5>
        <p class="small text-gray">Configure and monitor servo behavior</p>
      </header>

      <div class="grid gap-2">
        <!-- Left Column: Position Control -->
        <div class="s12 m6 l4">
          <section class="card p-2">
            <h6 class="m-bottom-2">Position Control</h6>
            <div class="center-align" role="group" aria-label="Position control">
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
                aria-label="Servo position control"
              />
              <div class="field label border round m-top-2">
                <label class="slider">
                  <input 
                    type="range" 
                    min="100" 
                    max="2000" 
                    step="1" 
                    v-model="newSpeed"
                    aria-label="Servo speed control"
                  >
                  <span class="small">Speed: {{ newSpeed }}</span>
                </label>
              </div>
            </div>
          </section>
        </div>

        <!-- Middle Column: Status and Calibration -->
        <div class="s12 m6 l4">
          <section class="card p-2 m-bottom-2">
            <h6 class="m-bottom-2">Current Status</h6>
            <div class="status-grid">
              <div v-for="(value, key) in servoStatus" :key="key" class="status-item p-1">
                <span class="label text-gray">{{ key }}</span>
                <span class="value">{{ value }}</span>
              </div>
            </div>
          </section>

          <section class="card p-2" v-if="currentServo?.min_pos !== undefined">
            <h6 class="m-bottom-2">Calibration Range</h6>
            <div class="status-grid">
              <div class="status-item p-1">
                <span class="label text-gray">Min Position</span>
                <span class="value">{{ currentServo?.min_pos || 'Not calibrated' }}</span>
              </div>
              <div class="status-item p-1">
                <span class="label text-gray">Max Position</span>
                <span class="value">{{ currentServo?.max_pos || 'Not calibrated' }}</span>
              </div>
            </div>
          </section>
        </div>

        <!-- Right Column: Controls -->
        <div class="s12 m12 l4">
          <section class="card p-2">
            <h6 class="m-bottom-2">Servo Configuration</h6>
            
            <div class="field label border round m-bottom-2">
              <input 
                type="number" 
                v-model="newId"
                aria-label="New servo ID"
                min="1"
                max="253"
              >
              <label>New Servo ID</label>
              <button 
                class="small"
                @click="changeId"
                :disabled="!newId"
                aria-label="Change servo ID"
              >
                Change ID
              </button>
            </div>

            <div class="actions">
              <button 
                class="border m-right-2 p-2"
                @click="wiggle"
                aria-label="Test servo movement"
              >
                <i class="fa-solid fa-arrows-left-right m-right-1"></i>
                Test Movement
              </button>
              <button 
                class="border p-2"
                @click="calibrate"
                aria-label="Calibrate servo range"
              >
                <i class="fa-solid fa-ruler m-right-1"></i>
                Calibrate Range
              </button>
            </div>
          </section>
        </div>
      </div>
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


function wiggle() {
  node.emit('wiggle', [parseInt(id)]);
}

function calibrate() {
  node.emit('calibrate', [parseInt(id)]);
}

watch(newSpeed, (newValue) => {
  if (!currentServo.value) return;
  node.emit('set_speed', [parseInt(id), parseInt(newValue)]);
});

function handlePositionUpdate(newValue) {
  if (typeof newValue === 'object' && newValue.value !== undefined) {
    newValue = newValue.value;
  }
  node.emit('set_servo', [parseInt(id), parseInt(newValue), parseInt(newSpeed.value)]);
}
</script>

<style scoped>
.servo-debug {
  padding: 1rem;
}

.status-grid {
  display: grid;
  gap: 0.5rem;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border);
}

.status-item:last-child {
  border-bottom: none;
}

.label {
  font-size: 0.875rem;
}

.value {
  font-weight: 500;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.actions button {
  flex: 1;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 600px) {
  .actions {
    flex-direction: column;
  }
  
  .actions button {
    width: 100%;
    margin-right: 0;
    margin-bottom: 0.5rem;
  }
}
</style>
