<template>
  <div class="grid-stack-item card" id="sound-widget" gs-w="4" gs-h="6" gs-min-w="3" gs-min-h="4">
    <div class="grid-stack-item-content">
      <article id="sound-list" style="overflow: auto">
        <div class="card medium">
          <div class="card-content">
            <span class="card-title">Available Sounds</span>
            <div id="sounds" class="small-spacing">
              <a v-for="sound in sounds"
                @click="play_sound(sound)"
                class="hover round small-padding sound-item">
                  <i class="material-icons left">volume_up</i>
                  {{sound.replace(/\.mp3$/i, '')}}
              </a>
            </div>
          </div>
        </div>
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

<style scoped>
/* Use BeerCSS classes for styling */
.sound-item {
  display: flex;
  align-items: center;
  cursor: pointer;
  text-decoration: none;
  color: var(--text);
  border-radius: 4px;
  margin-bottom: 4px;
}

#sounds {
  max-height: 500px;
  overflow-y: auto;
  padding: 8px 0;
}

/* Make sure we don't double-nest cards */
.grid-stack-item.card {
  border: none;
  box-shadow: none;
  background: transparent;
}

.grid-stack-item-content {
  padding: 0 !important;
}
</style>
