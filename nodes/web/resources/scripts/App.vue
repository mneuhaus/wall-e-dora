<script setup>
import { ref, provide } from 'vue';
import Gamepad from './components/Gamepad.vue';
import Power from './components/Power.vue';
import Volume from './components/Volume.vue';
import ConnectionStatus from './components/ConnectionStatus.vue';
import ServoStatus from './components/ServoStatus.vue';
import GridLock from './components/GridLock.vue';
import AddWidget from './components/AddWidget.vue';

// Create a reference to the dashboard component
const dashboardRef = ref(null);

// Provide the dashboard reference to child components
provide('dashboardRef', dashboardRef);
</script>

<template>
  <header>
    <nav>
      <RouterLink class="top-app-bar__title" style="font-size: 24px;align-items: left;" to="/">wall-e</RouterLink>
      <!-- <strong>Current route path:</strong> {{ $route.fullPath }} -->

      <a class=max>&nbsp;</a>
      <!-- <RouterLink to="/">Go to Home</RouterLink> -->
      <gamepad></gamepad>
      <servo-status></servo-status>
      <power></power>
      <volume></volume>
      <add-widget></add-widget>
      <grid-lock></grid-lock>
      <connection-status></connection-status>
    </nav>
  </header>

  <main>
    <RouterView ref="dashboardRef" />
  </main>
</template>
