<script setup>
import { ref, reactive, onMounted, provide, inject, computed, watch } from 'vue';
import { v4 as uuidv4 } from 'uuid';
import Sounds from '../components/Sounds.vue';
import node from "../Node.js";
import WidgetContainer from '../components/WidgetContainer.vue';

// State for widgets and layout
const layout = ref([]);
const gridLayoutRef = ref(null);
const isEditable = ref(false);
const widgetsState = ref({});

// Computed properties for grid
const isDraggable = computed(() => isEditable.value);
const isResizable = computed(() => isEditable.value);

// Watch for isEditable changes
watch(isEditable, (newVal) => {
  console.log("Dashboard isEditable changed to:", newVal);
}, { immediate: true });

// Inject appState from main.js if available
const appState = inject('appState', null);

// Toggle grid editing mode
function toggleGridEditing() {
  console.log('Before toggle - isEditable was:', isEditable.value);
  isEditable.value = !isEditable.value;
  console.log('Grid editing mode toggled to:', isEditable.value);
  
  // Force layout update to refresh the grid with new settings
  if (layout.value && layout.value.length > 0) {
    console.log('Forcing layout update with items:', layout.value.length);
    setTimeout(() => {
      const updatedLayout = [...layout.value];
      layout.value = updatedLayout;
      console.log('Layout updated, isDraggable should be:', isEditable.value);
    }, 0);
  }
}

// Provide grid state and functions to child components
provide('isGridEditable', isEditable);
provide('addWidget', addWidget);
provide('removeWidget', removeWidget);
provide('toggleGridEditing', toggleGridEditing);

// Provide access to widgets state
provide('widgetsState', widgetsState);

// Listen for servo status
node.on('servo_status', (event) => {
  // Update app state if available
  if (appState) {
    appState.setServos(event.value);
  }
  
  // Legacy support
  window.availableServos = event.value;
});

// Function to add a widget to the grid
function addWidget(type, config = {}) {
  const widgetId = `widget-${uuidv4()}`;
  const widgetConfig = {
    ...config,
    type,
    i: widgetId,
    x: 0,
    y: Math.max(0, ...layout.value.map(item => item.y + item.h)),
    w: config.w || 3,
    h: config.h || 4,
    minW: config.minW || 2,
    minH: config.minH || 2,
  };
  
  // Add to layout
  layout.value.push(widgetConfig);
  
  // Save widget to state
  widgetsState.value[widgetId] = widgetConfig;
  saveWidgetsState();
  
  return widgetId;
}

// Function to remove a widget from the grid
function removeWidget(widgetId) {
  const index = layout.value.findIndex(item => item.i === widgetId);
  if (index !== -1) {
    layout.value.splice(index, 1);
    
    // Remove from widgets state
    delete widgetsState.value[widgetId];
    saveWidgetsState();
  }
}

// Convert legacy widget state to Vue Grid Layout format
function convertLegacyWidgetsState(oldState) {
  const newLayout = [];
  
  if (!oldState) return newLayout;
  
  Object.entries(oldState).forEach(([widgetId, config]) => {
    // Create a layout item from the old config
    newLayout.push({
      i: widgetId,
      x: config.x || 0,
      y: config.y || 0,
      w: config.w || 3,
      h: config.h || 4,
      type: config.type,
      ...config // Include any additional properties from the original config
    });
  });
  
  return newLayout;
}

// Convert layout to widgets state format for saving
function layoutToWidgetsState(layoutItems) {
  const state = {};
  
  layoutItems.forEach(item => {
    state[item.i] = { ...item };
  });
  
  return state;
}

// Save widgets state to backend
function saveWidgetsState() {
  node.emit('save_widgets_state', widgetsState.value);
}

// Handle layout changes
function onLayoutUpdated(newLayout) {
  console.log('Layout updated:', newLayout);
  layout.value = newLayout;
  widgetsState.value = layoutToWidgetsState(newLayout);
  saveWidgetsState();
}

onMounted(() => {
  // Request initial servo status
  node.emit('SCAN', []);
  
  // Request widgets state from backend
  node.emit('get_widgets_state', []);
  
  // Listen for widgets state
  node.on('widgets_state', (event) => {
    const receivedWidgetsData = event.value || {};
    
    // Update appState if available
    if (appState) {
      appState.updateWidgetsState(receivedWidgetsData);
    }
    
    // Convert to layout format if needed
    widgetsState.value = receivedWidgetsData;
    layout.value = convertLegacyWidgetsState(receivedWidgetsData);
    
    console.log("Received and converted widgets state:", layout.value);
  });
});
</script>

<template>
  <div class="dashboard">
    <div class="grid-container">
      <grid-layout
        v-model:layout="layout"
        :col-num="12"
        :row-height="80"
        :is-draggable="isDraggable"
        :is-resizable="isResizable"
        :vertical-compact="true"
        :margin="[10, 10]"
        :use-css-transforms="true"
        @layout-updated="onLayoutUpdated"
        ref="gridLayoutRef"
      >
        <grid-item
          v-for="item in layout"
          :key="item.i"
          :x="item.x"
          :y="item.y"
          :w="item.w"
          :h="item.h"
          :i="item.i"
          :min-w="item.minW || 2"
          :min-h="item.minH || 2"
        >
          <widget-container
            :type="item.type"
            :widget-props="item"
            @remove="removeWidget(item.i)"
          />
        </grid-item>
      </grid-layout>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  width: 100%;
  height: 100%;
  position: relative;
}

.grid-container {
  width: 100%;
  height: 100%;
  padding: 10px;
}

:deep(.vue-grid-item) {
  background-color: var(--surface);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

:deep(.vue-grid-item:hover) {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

:deep(.vue-grid-item.vue-draggable-dragging) {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
  z-index: 10;
}

.widget-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.separator {
  width: 100%;
  height: 1px;
  background-color: rgba(255, 255, 255, 0.1);
  margin: 8px 0;
}
</style>