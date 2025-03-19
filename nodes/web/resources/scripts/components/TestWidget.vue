<template>
  <div class="test-widget">
    <h4>Test Widget</h4>
    <div class="widget-content">
      <p>This is a test widget to verify the grid functionality.</p>
      <div class="counter-container">
        <button @click="decrement" class="counter-button">-</button>
        <span class="counter-value">{{ counter }}</span>
        <button @click="increment" class="counter-button">+</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const counter = ref(0);

function increment() {
  counter.value++;
}

function decrement() {
  counter.value--;
}
</script>

<style scoped>
.test-widget {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 10px;
}

h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: var(--primary, #ffb300);
}

.widget-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.counter-container {
  display: flex;
  align-items: center;
  margin-top: 20px;
}

.counter-value {
  font-size: 24px;
  margin: 0 15px;
  min-width: 40px;
  text-align: center;
}

.counter-button {
  background-color: var(--primary, #ffb300);
  color: black;
  border: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-weight: bold;
}

.counter-button:hover {
  opacity: 0.9;
}
</style>