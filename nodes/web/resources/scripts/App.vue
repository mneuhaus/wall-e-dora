<script setup>
import Gamepad from './components/Gamepad.vue';
import Power from './components/Power.vue';
import Volume from './components/Volume.vue';
import ConnectionStatus from './components/ConnectionStatus.vue';
import ServoStatus from './components/ServoStatus.vue';
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
      <connection-status></connection-status>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>
</template>
