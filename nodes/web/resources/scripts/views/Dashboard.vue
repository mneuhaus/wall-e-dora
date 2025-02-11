<script setup>
import { useTemplateRef, onMounted } from 'vue';
import { GridStack } from 'gridstack';
import Sounds from '../components/Sounds.vue';
import node from "../Node.js";

onMounted(() => {
  if (typeof(gridState) != 'object') {
      gridState = {};
  }
  const grid = GridStack.init({
      alwaysShowResizeHandle: 'mobile' // true if we're on mobile devices
  });
  if (gridState) {
      Object.keys(gridState).forEach((id) => {
          if (document.getElementById(id)) {
              grid.update(document.getElementById(id), gridState[id]);
          }
      })
  }
  grid.on('change', (event, items) => {
      items.forEach((item) => {
          gridState[item.el.id] = {
              x: parseInt(item.x),
              y: parseInt(item.y),
              h: parseInt(item.h),
              w: parseInt(item.w),
          }
      })
      node.sendOutput('save_grid_state', gridState);
  });
})

</script>

<template>
  <div class="grid-stack" ref="grid-stack">
    <sounds />
  </div>
</template>