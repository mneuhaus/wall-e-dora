<template>
  <button class="transparent gamepad">
    <span :style="iconStyle">
      <i class="fa-solid fa-gamepad" style="width: 30px;"></i>
    </span>
    <menu class="no-wrap">
      <router-link
        v-for="gamepad in gamepads"
        :to="{ name: 'gamepad', params: { index: gamepad.index } }">
        {{gamepad.id}}
      </router-link>
    </menu>
  </button>
</template>

<style type="text/css" scoped>
  menu {
    left: auto;
    right: 0;
  }
</style>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';

const gamepads = ref([]);

function checkGamepad() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [];
  connected.value = pads && Array.from(pads).some(pad => pad);
}

class Gamepad {
  constructor(gamepadApi) {
    this.id = gamepadApi.id;
    this.index = gamepadApi.index;
  }
}

window.addEventListener("gamepadconnected", (event) => {
  console.log("Gamepad connected:", event);
  gamepads.value.push(new Gamepad(event.gamepad));
});

window.addEventListener("gamepaddisconnected", (event) => {
  console.log("Lost connection with the gamepad.", event);
});

const iconStyle = computed(() => ({
  color: gamepads.value.length > 0 ? 'green' : 'gray'
}));
</script>