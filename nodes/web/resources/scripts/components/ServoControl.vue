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
import { ref, computed, watch, onMounted, defineAsyncComponent } from 'vue';
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
  if (!servoData.value) return `Servo ${props.servoId}`;
  return servoData.value.alias ? `${servoData.value.alias} (${props.servoId})` : `Servo ${props.servoId}`;
});

const minPos = computed(() => servoData.value?.min_pos || 0);
const maxPos = computed(() => servoData.value?.max_pos || 1024);

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
  servoData.value = servos.find(s => s.id === parseInt(props.servoId)) || null;
  
  if (servoData.value) {
    currentPosition.value = servoData.value.position;
    currentSpeed.value = servoData.value.speed;
  }
}

// Listen for servo status updates
node.on('servo_status', (event) => {
  window.availableServos = event.value;
  updateServoData();
});

onMounted(() => {
  updateServoData();
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