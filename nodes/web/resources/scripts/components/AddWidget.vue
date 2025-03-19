<template>
  <div class="add-widget">
    <a @click="showWidgetMenu" class="add-button" :class="{ 'disabled': !isEditable }">
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
        <div class="menu-item" @click="addTestWidget">
          <i class="fas fa-cube m-right-1"></i>
          Test Widget
        </div>
        <div class="menu-item" @click="addSoundsWidget">
          <i class="fas fa-volume-up m-right-1"></i>
          Sounds Widget
        </div>
        <!-- Add more widget types here -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onMounted, onUnmounted } from 'vue';
import node from "../Node.js";

const menuVisible = ref(false);

// Get addWidget function from Dashboard
const addWidget = inject('addWidget', null);

// Get isEditable state from Dashboard
const isEditable = inject('isGridEditable', false);

// Get widgetsState from Dashboard
const widgetsState = inject('widgetsState', ref({}));

// Get appState if available (new approach)
const appState = inject('appState', null);

// Reference for servo selection dialog
const servoDialog = ref(null);

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
  // Only show menu if grid is in edit mode
  if (!isEditable.value) {
    return;
  }
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
      
      // Add widget using the Dashboard's addWidget function
      if (addWidget) {
        const widgetId = addWidget('servo-control', {
          servoId,
          w: 3,
          h: 4
        });
        
        console.log("Servo widget created with ID:", widgetId);
      } else {
        console.error("addWidget function not available");
      }
      
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
  
  // Add widget using the Dashboard's addWidget function
  if (addWidget) {
    const widgetId = addWidget('separator', {
      w: 12,
      h: 1,
      minH: 1,
      maxH: 1
    });
    
    console.log("Separator widget added with ID:", widgetId);
  } else {
    console.error("addWidget function not available");
  }
  
  menuVisible.value = false;
}

function addTestWidget() {
  console.log("Adding test widget");
  
  // Add widget using the Dashboard's addWidget function
  if (addWidget) {
    const widgetId = addWidget('test-widget', {
      w: 4,
      h: 3,
      minW: 2,
      minH: 2
    });
    
    console.log("Test widget added with ID:", widgetId);
  } else {
    console.error("addWidget function not available");
  }
  
  menuVisible.value = false;
}

function addSoundsWidget() {
  console.log("Adding sounds widget");
  
  // Add widget using the Dashboard's addWidget function
  if (addWidget) {
    const widgetId = addWidget('sounds-widget', {
      w: 4,
      h: 6,
      minW: 3,
      minH: 4
    });
    
    console.log("Sounds widget added with ID:", widgetId);
  } else {
    console.error("addWidget function not available");
  }
  
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
  transition: all 0.2s;
  color: white;
}

.add-button:hover:not(.disabled) {
  background-color: rgba(255, 255, 255, 0.1);
  color: var(--primary, #ffb300);
}

.add-button.disabled {
  opacity: 0.4;
  cursor: not-allowed;
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