<template>
  <div class="widget-container">
    <div class="widget-header" :class="{ 'edit-mode': isEditable }">
      <div v-if="isEditable" class="drag-handle">
        <i class="fas fa-grip-lines"></i>
      </div>
      <div class="widget-title">{{ getWidgetTitle() }}</div>
      <div class="widget-actions">
        <button v-if="isEditable" @click="$emit('remove')" class="widget-remove-btn">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>
    <div class="widget-content">
      <component 
        :is="componentType" 
        v-bind="componentProps"
        @remove="$emit('remove')"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, markRaw, inject } from 'vue';
import ServoControl from './ServoControl.vue';
import TestWidget from './TestWidget.vue';
import SoundsWidget from './SoundsWidget.vue';

// Widget configuration passed in as props
const props = defineProps({
  type: {
    type: String,
    required: true,
    validator: (value) => ['servo-control', 'separator', 'test-widget', 'sounds-widget'].includes(value)
  },
  // Dynamic props that will be passed to the specific widget component
  widgetProps: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['remove']);

// Get grid editable state from parent
const isEditable = inject('isGridEditable', false);

// Map widget types to components
const componentMap = {
  'servo-control': markRaw(ServoControl),
  'separator': 'div',
  'test-widget': markRaw(TestWidget),
  'sounds-widget': markRaw(SoundsWidget)
};

// Determine which component to render
const componentType = computed(() => {
  return componentMap[props.type] || 'div';
});

// Filter and transform props for the component
const componentProps = computed(() => {
  const filteredProps = { ...props.widgetProps };
  
  // Remove grid layout properties that shouldn't be passed to the component
  ['i', 'x', 'y', 'w', 'h', 'minW', 'minH', 'moved', 'static'].forEach(prop => {
    delete filteredProps[prop];
  });
  
  return filteredProps;
});

// Get a title for the widget
function getWidgetTitle() {
  switch (props.type) {
    case 'servo-control':
      const servoId = props.widgetProps.servoId;
      // Check if the servo ID is defined
      if (servoId === undefined || servoId === null) {
        console.warn('Servo widget missing servoId property:', props.widgetProps);
        return 'Servo (unassigned)';
      }
      return `Servo ${servoId}`;
    case 'separator':
      return 'Separator';
    case 'test-widget':
      return 'Test Widget';
    case 'sounds-widget':
      return 'Available Sounds';
    default:
      return 'Widget';
  }
}
</script>

<style scoped>
.widget-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  pointer-events: auto;
}

.widget-header.edit-mode {
  cursor: default;
  background-color: rgba(0, 0, 0, 0.15);
}

.widget-title {
  font-size: 0.9rem;
  font-weight: 500;
  opacity: 0.9;
  flex: 1;
  pointer-events: none;
}

.widget-actions {
  display: flex;
  gap: 6px;
}

.drag-handle {
  cursor: move;
  padding: 4px 8px;
  margin-right: 6px;
  color: var(--text);
  opacity: 0.7;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.drag-handle:hover {
  opacity: 1;
  background-color: rgba(255, 255, 255, 0.1);
}

.widget-remove-btn {
  background: transparent;
  border: none;
  color: var(--text);
  opacity: 0.6;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.widget-remove-btn:hover {
  opacity: 1;
  background-color: rgba(255, 0, 0, 0.15);
}

.widget-content {
  flex: 1;
  overflow: auto;
  padding: 12px;
}

.separator {
  width: 100%;
  height: 1px;
  background-color: rgba(255, 255, 255, 0.1);
  margin: 8px 0;
}
</style>