<template>
  <div class="sounds-widget">
    <div class="card medium">
      <div class="card-content">
        <span class="card-title">Available Sounds</span>
        <div id="sounds" class="small-spacing">
          <a v-for="sound in sounds" :key="sound"
            @click="play_sound(sound)"
            class="hover round small-padding sound-item">
              <i class="fas fa-volume-up"></i>
              <span class="sound-name">{{sound.replace(/\.mp3$/i, '')}}</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, onMounted} from 'vue';
import node from '../Node.js';

const sounds = ref([]);

// Request sounds list on mount
onMounted(() => {
  node.emit('get_sounds', []);
});

// Listen for sounds list
node.on('available_sounds', (event) => {
  sounds.value = event.value;
});

function play_sound(sound) {
  node.emit('play_sound', [sound]);
}
</script>

<style scoped>
.sounds-widget {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.card {
  margin: 0;
  height: 100%;
}

.card-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sound-item {
  display: flex;
  align-items: center;
  cursor: pointer;
  text-decoration: none;
  color: var(--text);
  border-radius: 4px;
  margin-bottom: 4px;
  padding: 8px;
}

.sound-name {
  margin-left: 8px;
}

.sound-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

#sounds {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
</style>