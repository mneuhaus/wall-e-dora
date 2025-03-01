<template>
  <div class="widget-container">
    <component 
      :is="componentType" 
      v-bind="props"
      @remove="$emit('remove')"
    />
  </div>
</template>

<script setup>
import { computed, markRaw } from 'vue';
import ServoControl from './ServoControl.vue';

// Widget configuration passed in as props
const props = defineProps({
  type: {
    type: String,
    required: true,
    validator: (value) => ['servo-control', 'separator'].includes(value)
  },
  // Dynamic props that will be passed to the specific widget component
  widgetProps: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['remove']);

// Map widget types to components
const componentMap = {
  'servo-control': markRaw(ServoControl),
  'separator': 'div'
};

// Determine which component to render
const componentType = computed(() => {
  return componentMap[props.type] || 'div';
});
</script>

<style scoped>
.widget-container {
  width: 100%;
  height: 100%;
}

.separator {
  width: 100%;
  height: 1px;
  background-color: rgba(255, 255, 255, 0.1);
  margin: 8px 0;
}
</style>