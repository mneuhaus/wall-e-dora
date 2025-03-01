<template>
  <div class="add-widget">
    <a @click="showWidgetMenu" class="add-button">
      <i class="fas fa-plus"></i>
    </a>
    
    <!-- Widget menu dropdown -->
    <div v-if="menuVisible" class="widget-menu">
      <div class="menu-items">
        <div class="menu-item" @click="addServoWidget">
          <i class="fas fa-sliders m-right-1"></i>
          Servo Control
        </div>
        <div class="menu-item" @click="addSeparator">
          <i class="fas fa-grip-lines m-right-1"></i>
          Separator
        </div>
        <!-- Add more widget types here -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onMounted, onUnmounted } from 'vue';
import { v4 as uuidv4 } from 'uuid';
import node from "../Node.js";

const menuVisible = ref(false);
const gridStackInstance = inject('gridStackInstance');
const servoDialog = ref(null);

// Get appState if available (new approach)
const appState = inject('appState', null);

// Function to save widget configuration to backend
function saveWidgetToState(widgetId, config) {
  // Get widget position and size from grid
  const grid = appState ? appState.getGridStack() : window.gridStackInstance;
  const el = document.getElementById(widgetId);
  
  if (grid && el) {
    const gridNode = grid.engine.nodes.find(n => n.el.id === widgetId);
    
    if (gridNode) {
      // Create a full widget configuration 
      const widgetConfig = {
        ...config,
        x: gridNode.x,
        y: gridNode.y,
        w: gridNode.w,
        h: gridNode.h
      };
      
      // Get current widgets state
      let widgetsState = appState ? appState.getWidgetsState() : (window.widgetsState || {});
      
      // Add/update this widget
      widgetsState[widgetId] = widgetConfig;
      
      // Save to state manager
      if (appState) {
        appState.updateWidgetsState(widgetsState);
      } else {
        // Legacy support
        window.widgetsState = widgetsState;
      }
      
      // Send to backend for saving
      console.log("Saving widget state:", widgetId, widgetConfig);
      node.emit('save_widgets_state', widgetsState);
    }
  }
}

// Helper function to get available servos
function getAvailableServos() {
  return appState ? appState.getServos() : (window.availableServos || []);
}

// Handle dialog cleanup on component unmount
onUnmounted(() => {
  if (servoDialog.value && servoDialog.value.parentNode) {
    servoDialog.value.parentNode.removeChild(servoDialog.value);
  }
});

// Close menu when clicking outside
function handleClickOutside(event) {
  if (menuVisible.value && !event.target.closest('.add-widget') && !event.target.closest('.widget-menu')) {
    menuVisible.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

function showWidgetMenu() {
  menuVisible.value = !menuVisible.value;
}

function addServoWidget() {
  console.log("Adding servo widget");
  // Get available servos
  const servos = getAvailableServos();
  console.log("Available servos:", servos);
  
  if (servos.length === 0) {
    alert("No servos available. Please connect a servo first.");
    menuVisible.value = false;
    return;
  }
  
  // Create dialog if it doesn't exist
  if (!servoDialog.value) {
    servoDialog.value = document.createElement('div');
    servoDialog.value.className = 'servo-selector-dialog';
    document.body.appendChild(servoDialog.value);
  }
  
  // Update dialog content
  servoDialog.value.innerHTML = `
    <div class="dialog-content">
      <h6>Select a servo</h6>
      <div class="servo-list">
        ${servos.map(servo => `
          <div class="servo-option" data-id="${servo.id}">
            ${servo.alias ? `${servo.alias} (${servo.id})` : `Servo ${servo.id}`}
          </div>
        `).join('')}
      </div>
      <div class="dialog-actions">
        <button class="cancel-btn border">Cancel</button>
      </div>
    </div>
  `;
  
  // Show the dialog
  servoDialog.value.style.display = 'block';
  
  // Clean up previous event listeners
  const newDialog = servoDialog.value.cloneNode(true);
  servoDialog.value.parentNode.replaceChild(newDialog, servoDialog.value);
  servoDialog.value = newDialog;
  
  // Handle servo selection
  servoDialog.value.querySelectorAll('.servo-option').forEach(option => {
    option.addEventListener('click', () => {
      const servoId = option.getAttribute('data-id');
      console.log("Selected servo ID:", servoId);
      
      // Create widget using direct GridStack API
      const grid = window.gridStackInstance;
      if (!grid) {
        console.error("GridStack instance not found");
        return;
      }
      
      console.log("Grid instance found, adding widget");
      
      // Make sure grid is unlocked
      if (grid.opts.staticGrid) {
        console.log("Grid is locked, unlocking temporarily");
        grid.setStatic(false);
      }
      
      // Create widget directly with GridStack API
      const widgetId = `servo-widget-${uuidv4()}`;
      
      // Create content that will be properly interpreted by the browser
      const content = `
        <div class="grid-stack-item-content widget-mount-point" data-id="${widgetId}" data-type="servo-control" data-servo-id="${servoId}">
          <servo-control servo-id="${servoId}"></servo-control>
        </div>
      `;
      
      // Create the widget with proper HTML content
      const widget = grid.addWidget({
        id: widgetId,
        w: 3,
        h: 4,
        content
      });
      
      console.log("Servo widget created with HTML content");
      
      // Save widget data to state
      saveWidgetToState(widgetId, {
        type: 'servo-control',
        servoId: servoId,
        w: 3,
        h: 4
      });
      
      console.log("Widget added:", widget);
      
      // Hide dialog
      servoDialog.value.style.display = 'none';
      menuVisible.value = false;
    });
  });
  
  // Handle cancel
  servoDialog.value.querySelector('.cancel-btn').addEventListener('click', () => {
    servoDialog.value.style.display = 'none';
    menuVisible.value = false;
  });
  
  // Close the dropdown menu
  menuVisible.value = false;
}

function addSeparator() {
  console.log("Adding separator widget");
  
  // Get grid instance directly from window
  const grid = window.gridStackInstance;
  if (!grid) {
    console.error("GridStack instance not found");
    return;
  }
  
  console.log("Grid instance found, adding separator");
  
  // Make sure grid is unlocked
  if (grid.opts.staticGrid) {
    console.log("Grid is locked, unlocking temporarily");
    grid.setStatic(false);
  }
  
  // Create widget directly with GridStack API
  const widgetId = `separator-${uuidv4()}`;
  
  // Create content with proper wrapper
  const content = `
    <div class="grid-stack-item-content widget-mount-point" data-id="${widgetId}" data-type="separator">
      <div class="separator"></div>
    </div>
  `;
  
  const widget = grid.addWidget({
    id: widgetId,
    w: 12,
    h: 1,
    content
  });
  
  console.log("Separator widget added:", widget);
  
  // Save widget data to state
  saveWidgetToState(widgetId, {
    type: 'separator',
    w: 12,
    h: 1
  });
  
  menuVisible.value = false;
}
</script>

<style scoped>
.add-button {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  transition: background-color 0.2s;
  color: white;
}

.add-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.widget-menu {
  position: absolute;
  right: 0;
  top: 60px;
  z-index: 1000;
  background-color: var(--surface);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 200px;
  overflow: hidden;
  color: var(--text);
}

.menu-items {
  padding: 8px 0;
}

.menu-item {
  padding: 10px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
}

.menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.separator {
  width: 100%;
  height: 1px;
  background-color: rgba(255, 255, 255, 0.1);
  margin: 8px 0;
}

/* Servo selector dialog styles */
.servo-selector-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.dialog-content {
  background-color: var(--surface);
  color: var(--text);
  border-radius: 8px;
  padding: 20px;
  width: 300px;
  max-width: 90%;
}

.dialog-content h6 {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 18px;
}

.servo-list {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.servo-option {
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-bottom: 4px;
}

.servo-option:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
}

.cancel-btn {
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 4px;
  background-color: transparent;
  color: var(--text);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.cancel-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}
</style>