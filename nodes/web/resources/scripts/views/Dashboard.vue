<script setup>
import { ref, onMounted, provide, inject, nextTick } from 'vue';
import { GridStack } from 'gridstack';
import Sounds from '../components/Sounds.vue';
import node from "../Node.js";
import WidgetContainer from '../components/WidgetContainer.vue';

// Create a reference to the grid
const gridInstance = ref(null);
const gridStackRef = ref(null);

// Inject appState from main.js if available, or use node directly
const appState = inject('appState', null);

// Provide grid instance to child components
provide('gridStackInstance', gridInstance);

// Listen for servo status
node.on('servo_status', (event) => {
  // Update app state if available
  if (appState) {
    appState.setServos(event.value);
  }
  
  // Legacy support
  window.availableServos = event.value;
});

/**
 * Function to restore widgets from saved state using a better Vue approach
 * This still works with GridStack but renders WidgetContainer component
 */
function restoreWidgetsFromState(widgetsState, grid) {
  if (!widgetsState || Object.keys(widgetsState).length === 0) return;
  
  console.log("Restoring widgets from state:", widgetsState);
  
  // Process after DOM is updated
  nextTick(() => {
    Object.entries(widgetsState).forEach(([widgetId, config]) => {
      // Skip if this widget already exists
      if (document.getElementById(widgetId)) return;
      
      console.log("Restoring widget:", widgetId, config);
      
      // Create the base widget with GridStack
      const widget = grid.addWidget({
        id: widgetId,
        x: config.x,
        y: config.y,
        w: config.w,
        h: config.h,
        content: `<div class="grid-stack-item-content widget-mount-point" data-id="${widgetId}" data-type="${config.type}" data-props='${JSON.stringify(config)}'></div>`
      });
    });
    
    // Once all widgets are created, initialize them with Vue components
    document.querySelectorAll('.widget-mount-point').forEach(el => {
      // Create widget container for this element
      const mountPoint = el;
      const widgetId = mountPoint.dataset.id;
      const widgetType = mountPoint.dataset.type;
      const widgetProps = JSON.parse(mountPoint.dataset.props);
      
      console.log("Mounting widget:", widgetId, widgetType, widgetProps);
      
      // Create the widget container element
      const containerEl = document.createElement('div');
      containerEl.className = 'widget-container';
      mountPoint.appendChild(containerEl);
      
      // Create the widget component
      const widgetEl = document.createElement('div');
      widgetEl.id = `widget-component-${widgetId}`;
      containerEl.appendChild(widgetEl);
      
      // We still need to manually create the component based on type
      if (widgetType === 'servo-control') {
        widgetEl.innerHTML = `<servo-control servo-id="${widgetProps.servoId}"></servo-control>`;
      } else if (widgetType === 'separator') {
        widgetEl.innerHTML = `<div class="separator"></div>`;
      }
    });
  });
}

onMounted(() => {
  if (typeof(gridState) != 'object') {
      gridState = {};
  }
  
  // Initialize GridStack
  const grid = GridStack.init({
      alwaysShowResizeHandle: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
      column: 12,
      float: true,
      margin: '10px', 
      cellHeight: 80,
      staticGrid: true,
      animate: true
  });
  
  // Store grid instance
  gridInstance.value = grid;
  
  // Store in appState if available
  if (appState) {
    appState.registerGridStack(grid);
  }
  
  // Legacy support
  window.gridStackInstance = grid;
  
  // Request initial servo status
  node.emit('SCAN', []);
  
  // Load saved grid state if available
  if (gridState) {
      Object.keys(gridState).forEach((id) => {
          if (document.getElementById(id)) {
              grid.update(document.getElementById(id), gridState[id]);
          }
      });
  }
  
  // Request widgets state from backend
  node.emit('get_widgets_state', []);
  
  // Listen for widgets state
  node.on('widgets_state', (event) => {
    const widgetsData = event.value || {};
    
    // Update appState if available
    if (appState) {
      appState.updateWidgetsState(widgetsData);
    }
    
    // Legacy support
    window.widgetsState = widgetsData;
    
    console.log("Received widgets state:", widgetsData);
    restoreWidgetsFromState(widgetsData, grid);
  });
  
  // Save grid state when changes occur
  grid.on('change', (event, items) => {
      items.forEach((item) => {
          gridState[item.el.id] = {
              x: parseInt(item.x),
              y: parseInt(item.y),
              h: parseInt(item.h),
              w: parseInt(item.w),
          }
      });
      
      // Send grid state to backend for saving
      node.sendOutput('save_grid_state', gridState);
      
      // Also update any widgets in the widgets state
      const widgetsState = appState ? appState.getWidgetsState() : window.widgetsState;
      
      if (widgetsState) {
        items.forEach((item) => {
          const widgetId = item.el.id;
          if (widgetsState[widgetId]) {
            widgetsState[widgetId].x = parseInt(item.x);
            widgetsState[widgetId].y = parseInt(item.y);
            widgetsState[widgetId].h = parseInt(item.h);
            widgetsState[widgetId].w = parseInt(item.w);
          }
        });
        
        // Save updated widgets state
        node.emit('save_widgets_state', widgetsState);
      }
  });
})

</script>

<template>
  <div class="grid-stack" ref="gridStackRef">
    <sounds />
  </div>
</template>

<style scoped>
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