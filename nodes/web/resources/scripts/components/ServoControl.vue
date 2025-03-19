<template>
  <div class="servo-control-widget">
    <div class="widget-header">
      <h6 class="title" style="color: var(--text);">{{ servoTitle }}</h6>
      <div class="flex-spacer"></div>
      <a class="settings-button" @click="showSettings = !showSettings">
        <i class="fas fa-cog"></i>
      </a>
    </div>
    
    <!-- Main control display -->
    <div v-if="!showSettings" class="widget-content">
      <div class="control-area">
        <round-slider
          v-model="currentPosition"
          :min="minPos"
          :max="maxPos"
          radius="80"
          :path-color="'#37474F'"
          :range-color="'#00bfa5'"
          :start-angle="315"
          :end-angle="225"
          @change="handlePositionUpdate"
        />
      </div>
      <div class="status-info">
        <div class="info-item">
          <span class="label">Position:</span>
          <span class="value">{{ currentPosition }}</span>
        </div>
        <div class="info-item">
          <span class="label">Speed:</span>
          <span class="value">{{ currentSpeed }}</span>
        </div>
      </div>
    </div>
    
    <!-- Settings panel -->
    <div v-else class="widget-content settings-panel">
      <div class="field label border round m-bottom-2">
        <label class="slider">
          <input 
            type="range" 
            min="100" 
            max="2000" 
            step="10" 
            v-model="currentSpeed"
            @change="updateSpeed"
          >
          <span class="small">Speed: {{ currentSpeed }}</span>
        </label>
      </div>
      
      <button class="border full-width m-bottom-2" @click="wiggle">
        <i class="fas fa-arrows-left-right m-right-1"></i>
        Test Movement
      </button>
      
      <button class="border full-width" @click="calibrate">
        <i class="fas fa-ruler m-right-1"></i>
        Calibrate Range
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, defineAsyncComponent } from 'vue';
import node from '../Node.js';

// Attempt to load the round slider component
// If vue-three-round-slider isn't available, we'll create a simple fallback
const RoundSlider = defineAsyncComponent({
  loader: () => import('round-slider').then(() => ({
    props: ['modelValue', 'min', 'max', 'radius', 'lineWidth', 'pathColor', 'rangeColor', 'startAngle', 'endAngle', 'animation'],
    template: `
      <div ref="sliderContainer" class="round-slider-container"></div>
    `,
    mounted() {
      this.initSlider();
    },
    methods: {
      initSlider() {
        const el = this.$refs.sliderContainer;
        if (!el) return;
        
        // Create the slider using round-slider library
        this.slider = $(el).roundSlider({
          radius: this.radius || 85,
          width: this.lineWidth || 16,
          handleSize: '+0',
          sliderType: 'min-range',
          value: this.modelValue,
          min: this.min || 0,
          max: this.max || 1024,
          startAngle: this.startAngle || 315,
          endAngle: this.endAngle || 225,
          rangeColor: this.rangeColor || '#00bfa5',
          pathColor: this.pathColor || '#37474F',
          valueChange: (e) => {
            this.$emit('update:modelValue', e.value);
            this.$emit('change', e.value);
          }
        });
      }
    },
    beforeUnmount() {
      if (this.slider) {
        $(this.$refs.sliderContainer).roundSlider('destroy');
      }
    },
    watch: {
      modelValue(val) {
        if (this.slider && this.slider.getValue() !== val) {
          $(this.$refs.sliderContainer).roundSlider('setValue', val);
        }
      }
    }
  })),
  errorComponent: {
    template: `
      <div class="fallback-slider">
        <input type="range" :min="min" :max="max" :value="modelValue" @input="$emit('update:modelValue', $event.target.value); $emit('change', $event.target.value)" />
        <div class="slider-value">{{ modelValue }}</div>
      </div>
    `,
    props: ['modelValue', 'min', 'max']
  }
});

// Props
const props = defineProps({
  servoId: {
    type: [Number, String],
    required: true
  }
});

// State
const showSettings = ref(false);
const currentPosition = ref(0);
const currentSpeed = ref(100);
const servoData = ref(null);

// Computed
const servoTitle = computed(() => {
  // Check if servoId is defined
  if (props.servoId === undefined || props.servoId === null) {
    console.warn('ServoControl: undefined servoId in props', props);
    return 'Servo (unassigned)';
  }
  
  // Check if servo data is available
  if (!servoData.value) {
    return `Servo ${props.servoId}`;
  }
  
  // Return alias if available
  return servoData.value.alias 
    ? `${servoData.value.alias} (${props.servoId})` 
    : `Servo ${props.servoId}`;
});

const minPos = computed(() => {
  if (!servoData.value || servoData.value.min_pos === undefined) return 0;
  return servoData.value.min_pos;
});

const maxPos = computed(() => {
  if (!servoData.value || servoData.value.max_pos === undefined) return 1024;
  return servoData.value.max_pos;
});

// Methods
function handlePositionUpdate(newValue) {
  if (typeof newValue === 'object' && newValue.value !== undefined) {
    newValue = newValue.value;
  }
  updateServoPosition(parseInt(newValue));
}

function updateServoPosition(position) {
  node.emit('set_servo', [parseInt(props.servoId), position, parseInt(currentSpeed.value)]);
}

function updateSpeed() {
  node.emit('set_speed', [parseInt(props.servoId), parseInt(currentSpeed.value)]);
}

function wiggle() {
  node.emit('wiggle', [parseInt(props.servoId)]);
}

function calibrate() {
  node.emit('calibrate', [parseInt(props.servoId)]);
}

// Event handlers
function updateServoData() {
  const servos = window.availableServos || [];
  
  // Convert id to number for consistent comparison 
  const targetId = parseInt(props.servoId);
  
  console.log(`[SERVO-DEBUG] Looking for servo ID ${targetId} in ${servos.length} available servos`);
  
  if (servos.length > 0) {
    // Log IDs for comparison debug
    const availableIds = servos.map(s => typeof s.id === 'string' ? parseInt(s.id) : s.id);
    console.log(`[SERVO-DEBUG] Available servo IDs: ${JSON.stringify(availableIds)}`);
  }
  
  // Try to find the matching servo
  servoData.value = servos.find(s => {
    const servoId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
    const matches = servoId === targetId;
    console.log(`[SERVO-DEBUG] Comparing ${servoId} (${typeof servoId}) with ${targetId} (${typeof targetId}): ${matches}`);
    return matches;
  }) || null;
  
  if (servoData.value) {
    console.log(`[SERVO-DEBUG] Found servo data for ID ${props.servoId}:`, JSON.stringify(servoData.value));
    currentPosition.value = servoData.value.position || 0;
    currentSpeed.value = servoData.value.speed || 100;
  } else {
    console.warn(`[SERVO-DEBUG] Servo ${props.servoId} not found in available servos`);
  }
}

// Listen for servo status updates
const unsubscribe = node.on('servo_status', (event) => {
  console.log(`[SERVO-DEBUG] Widget for servo ${props.servoId} received servo_status event with ${event.value ? event.value.length : 0} servos`);
  
  // For debugging, log all servos received
  if (event.value && event.value.length > 0) {
    event.value.forEach(servo => {
      console.log(`[SERVO-DEBUG] Available servo: ID=${servo.id}, position=${servo.position}, min=${servo.min_pos}, max=${servo.max_pos}`);
    });
  }
  
  window.availableServos = event.value || [];
  updateServoData();
});

onMounted(() => {
  console.log(`[SERVO-DEBUG] Component mounted for servo ${props.servoId}`);
  updateServoData();
  
  // Request a scan to get fresh servo data
  if (props.servoId !== undefined && props.servoId !== null) {
    console.log(`[SERVO-DEBUG] Requesting servo scan for ${props.servoId}`);
    node.emit('SCAN', []);
  }
});

// Make sure to clean up event listeners when component is unmounted
onUnmounted(() => {
  if (typeof unsubscribe === 'function') {
    unsubscribe();
  }
});
</script>

<style scoped>
.servo-control-widget {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--surface);
  color: var(--text);
  border-radius: 8px;
}

.widget-header {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.1);
}

.title {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.flex-spacer {
  flex: 1;
}

.settings-button {
  cursor: pointer;
  color: #555;
  padding: 5px;
}

.widget-content {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.control-area {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.status-info {
  margin-top: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.label {
  color: #666;
  font-size: 14px;
}

.value {
  font-weight: 500;
}

.settings-panel {
  padding: 16px;
}

.full-width {
  width: 100%;
}

/* Round slider styling */
.round-slider-container {
  width: 170px;
  height: 170px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fallback-slider {
  width: 100%;
  text-align: center;
}

.slider-value {
  margin-top: 10px;
  font-weight: bold;
}
</style>