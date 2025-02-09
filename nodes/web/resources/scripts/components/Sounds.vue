<template>
  <div class="grid-stack-item" id="sound-widget">
    <div class="grid-stack-item-content">
      <article id="sound-list" style="overflow: auto">
        <strong>Available Sounds</strong>

        <article id="sounds">
          <a v-for="sound in sounds"
             @click="play_sound(sound)"
             class="row wave">
              {{sound.replace(/\.mp3$/i, '')}}
          </a>
        </article>

      </article>
    </div>
  </div>
</template>

<script setup>
import {ref} from 'vue';
import node from '../Node.js';

const sounds = ref([]);

node.on('available_sounds', (event) => {
  sounds.value = event.value;
})

function play_sound(sound) {
  node.emit('play_sound', [sound]);
}
</script>
