<template>
  <div class="grid-stack-item" id="camera-widget">
    <div class="grid-stack-item-content">
      <article id="camera-feed" style="overflow: auto">
        <strong>Camera Feed</strong>
        <div class="camera-container">
          <img v-if="imageData" :src="'data:image/jpeg;base64,' + imageData" alt="Camera Feed" />
          <div v-else class="camera-placeholder">Waiting for camera feed...</div>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import node from '../Node.js';

const imageData = ref(null);

node.on('camera_feed', (event) => {
  // The image data is expected to be base64 encoded
  imageData.value = event.value;
});
</script>

<style scoped>
.camera-container {
  width: 100%;
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

.camera-container img {
  max-width: 100%;
  max-height: 240px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.camera-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 180px;
  width: 100%;
  background-color: #f0f0f0;
  border-radius: 4px;
  color: #666;
  font-style: italic;
}
</style>