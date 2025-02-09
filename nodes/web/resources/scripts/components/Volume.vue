<template>
  <button>
    <span><i class="fa-solid fa-volume-high"></i></span>
    <i>arrow_drop_down</i>
    <menu>
      <article class="small-height round">
        <label class="slider max vertical">
          <input type="range" id="volume" min="0" max="1" value="1" step="0.01" @change="handleVolumeChange">
          <span></span>
        </label>
      </article>
    </menu>
  </button>
</template>
<script setup>
import './Node';

console.log(Node);

function handleVolumeChange(event) {
  sendOutput('set_volume', [event.target.value])
}
</script>
