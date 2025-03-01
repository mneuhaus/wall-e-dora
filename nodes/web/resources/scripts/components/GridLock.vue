<template>
  <div class="grid-lock">
    <a @click="toggleLock" class="lock-button">
      <i :class="['fas', isLocked ? 'fa-lock' : 'fa-lock-open']"></i>
    </a>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const isLocked = ref(true);

// Toggle lock state
function toggleLock() {
  console.log("Lock button clicked");
  isLocked.value = !isLocked.value;
  
  const gridInstance = window.gridStackInstance;
  
  if (gridInstance) {
    if (isLocked.value) {
      // Lock the grid
      console.log("Locking grid");
      gridInstance.setStatic(true);
    } else {
      // Unlock the grid
      console.log("Unlocking grid");
      gridInstance.setStatic(false);
    }
  } else {
    console.warn("GridStack instance not found");
  }
}
</script>

<style scoped>
.lock-button {
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

.lock-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.material-icons {
  font-size: 22px;
}

.locked {
  color: #ffffff;
}

.unlocked {
  color: #4fc3f7;
}
</style>