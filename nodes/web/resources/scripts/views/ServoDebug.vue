<template>
  <div class="servo-debug">
    <h2>Servo Debug - {{ id }}</h2>
    <p>This is where you can inspect and test servo behavior.</p>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router';
const route = useRoute();
const id = route.params.id;
</script>

<style scoped>
.servo-debug {
  padding: 1rem;
}
</style>
