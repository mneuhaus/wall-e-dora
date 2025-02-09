<template>
  <span v-if="connected" style="color: #00bfa5; font-size:24px; margin-left:16px;">
    <i class="fa-solid fa-link"></i>
  </span>
  <span v-else style="color: #e53935; font-size:24px; margin-left:16px;">
    <i class="fa-solid fa-link-slash"></i>
  </span>
</template>

<script setup>
import { ref } from 'vue';
import node from '../Node.js';

const connected = ref(false);
node.on('connection', (status) => {
  connected.value = status;
});
</script>
