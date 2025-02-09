<template>
  <button class="transparent">
    <span>
      <i class="fa-solid fa-battery-half"></i>
      <span style="margin-left: 10px; display: inline-block;">{{ soc }} %</span>
    </span>
    <menu class="no-wrap">
      <a>Voltage: {{ voltage }} V</a>
      <a>Current: {{ current }} A</a>
      <a>Power: {{ power }} W</a>
      <a style="font-size: 18px;">Runtime: {{ runtime }}</a>
    </menu>
  </button>
</template>

<script setup>
import { ref } from 'vue';
import node from '../Node.js';

const voltage = ref('');
const current = ref('');
const power = ref('');
const runtime = ref('');
const soc = ref('');

node.on('voltage', (event) => {
  voltage.value = parseFloat(event.value).toFixed(2);
});
node.on('current', (event) => {
  current.value = parseFloat(event.value).toFixed(2);
});
node.on('power', (event) => {
  power.value = parseFloat(event.value).toFixed(2);
});
node.on('soc', (event) => {
  soc.value = parseFloat(event.value).toFixed(0);
});
node.on('runtime', (event) => {
  runtime.value = event.value;
});
</script>
