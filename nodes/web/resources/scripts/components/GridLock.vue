<template>
  <div class="grid-lock">
    <a @click="toggleLock" class="lock-button">
      <i :class="['fas', isEditable && isEditable.value ? 'fa-lock-open' : 'fa-lock']"></i>
    </a>
  </div>
</template>

<script setup>
import { inject, ref, watch, onMounted } from 'vue';

// Get grid editing state and toggle function from Dashboard
const isEditable = inject('isGridEditable', ref(false));
const toggleGridEditing = inject('toggleGridEditing', () => {});

// For debugging 
onMounted(() => {
  console.log("GridLock mounted, isEditable:", isEditable);
});

// Watch for changes to isEditable
watch(isEditable, (newVal) => {
  console.log("isEditable changed to:", newVal);
}, { immediate: true });

// Toggle lock state
function toggleLock() {
  console.log("Lock button clicked, before toggle:", isEditable.value);
  toggleGridEditing();
  // Log after toggle for debugging
  setTimeout(() => {
    console.log("After toggle:", isEditable.value);
  }, 10);
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
  transition: background-color 0.2s, color 0.2s;
  color: white;
}

.lock-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

/* Add a highlight color when grid is unlocked/editable */
.lock-button i.fa-lock-open {
  color: var(--primary, #ffb300);
}
</style>