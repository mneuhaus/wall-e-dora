<template>
  <div class="controller" id="controller_1">
    <h1 class="padded">{{ controllerName }}</h1>
    <div class="stick-wrapper">
      <!-- Left Analog Stick -->
      <div class="table sticks">
        <header class="header padded">LEFT_ANALOG_STICK</header>
        <div class="row">
          <div>Position X</div>
          <div>Position Y</div>
        </div>
        <div class="row">
          <div :id="`${index}_LEFT_ANALOG_STICK_x`" :style="leftStickStyles.x">{{ leftStick.x }}</div>
          <div :id="`${index}_LEFT_ANALOG_STICK_y`" :style="leftStickStyles.y">{{ leftStick.y }}</div>
        </div>
        <div class="row padded">
          <div class="analog-vis" :id="`${index}_LEFT_ANALOG_STICK`">
            <div :style="leftStickTransform"></div>
          </div>
        </div>
        <div class="row">
          <div>Degrees</div>
          <div>Radians</div>
        </div>
        <div class="row">
          <div :id="`${index}_LEFT_ANALOG_STICK_deg`">{{ leftStick.degrees }}</div>
          <div :id="`${index}_LEFT_ANALOG_STICK_rad`">{{ leftStick.radians }}</div>
        </div>
      </div>
      <!-- Right Analog Stick -->
      <div class="table sticks">
        <header class="header padded">RIGHT_ANALOG_STICK</header>
        <div class="row">
          <div>Position X</div>
          <div>Position Y</div>
        </div>
        <div class="row">
          <div :id="`${index}_RIGHT_ANALOG_STICK_x`" :style="rightStickStyles.x">{{ rightStick.x }}</div>
          <div :id="`${index}_RIGHT_ANALOG_STICK_y`" :style="rightStickStyles.y">{{ rightStick.y }}</div>
        </div>
        <div class="row padded">
          <div class="analog-vis" :id="`${index}_RIGHT_ANALOG_STICK`">
            <div :style="rightStickTransform"></div>
          </div>
        </div>
        <div class="row">
          <div>Degrees</div>
          <div>Radians</div>
        </div>
        <div class="row">
          <div :id="`${index}_RIGHT_ANALOG_STICK_deg`">{{ rightStick.degrees }}</div>
          <div :id="`${index}_RIGHT_ANALOG_STICK_rad`">{{ rightStick.radians }}</div>
        </div>
      </div>
    </div>
    <!-- Buttons -->
    <div class="table buttons">
      <header>
        <div class="row header">
          <div>Buttons</div>
          <div>Pressed</div>
          <div>Value</div>
        </div>
      </header>
      <div class="row" v-for="(btn, btnName) in buttons" :key="btnName">
        <div>{{ btnName }}</div>
        <div :id="`${index}_${btnName}`" :style="buttonStyle(btn.pressed)">{{ btn.pressed }}</div>
        <div :id="`${index}_${btnName}_value`" :style="buttonStyle(btn.pressed)">{{ btn.value }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';

const index = 1; // Static index; can be dynamic if needed
const controllerName = "StadiaG85F-1dce: Index 1";

const leftStick = reactive({
  x: -0.8897637724876404,
  y: -0.8068794012069702,
  degrees: "137.797°",
  radians: "2.405"
});

const rightStick = reactive({
  x: 0,
  y: 0,
  degrees: "—",
  radians: "—"
});

const leftStickStyles = reactive({
  x: "background-color: rgba(140, 255, 216, 0.89);",
  y: "background-color: rgba(140, 255, 216, 0.808);"
});

const rightStickStyles = reactive({
  x: "background-color: rgba(140, 255, 216, 0);",
  y: "background-color: rgba(140, 255, 216, 0);"
});

const leftStickTransform = computed(() => {
  return "transform: translate3d(-44.4882px, -40.344px, 0px);";
});

const rightStickTransform = computed(() => {
  return "transform: translate3d(0px, 0px, 0px);";
});

const buttons = reactive({
  FACE_1: { pressed: false, value: 0 },
  FACE_2: { pressed: false, value: 0 },
  FACE_3: { pressed: false, value: 0 },
  FACE_4: { pressed: false, value: 0 },
  LEFT_SHOULDER: { pressed: true, value: 1 },
  RIGHT_SHOULDER: { pressed: false, value: 0 },
  LEFT_SHOULDER_BOTTOM: { pressed: true, value: 1 },
  RIGHT_SHOULDER_BOTTOM: { pressed: false, value: 0 },
  SELECT: { pressed: false, value: 0 },
  START: { pressed: false, value: 0 },
  LEFT_ANALOG_BUTTON: { pressed: false, value: 0 },
  RIGHT_ANALOG_BUTTON: { pressed: false, value: 0 },
  DPAD_UP: { pressed: false, value: 0 },
  DPAD_DOWN: { pressed: false, value: 0 },
  DPAD_LEFT: { pressed: false, value: 0 },
  DPAD_RIGHT: { pressed: false, value: 0 },
  HOME: { pressed: false, value: 0 },
  MISCBUTTON_1: { pressed: false, value: 0 },
  MISCBUTTON_2: { pressed: false, value: 0 }
});

function buttonStyle(pressed) {
  return pressed ? "background-color: rgb(140, 255, 216);" : "background-color: rgba(140, 255, 216, 0);";
}
</script>

<style scoped>
.controller {
  font-family: Arial, sans-serif;
  margin: 10px;
}
.table {
  border: 1px solid #ccc;
  margin-bottom: 10px;
  padding: 5px;
}
.row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
}
.header {
  font-weight: bold;
}
.sticks {
  margin-bottom: 10px;
}
.analog-vis {
  width: 100px;
  height: 100px;
  background-color: #f0f0f0;
  position: relative;
}
.analog-vis div {
  width: 20px;
  height: 20px;
  background-color: #8cffd8;
  position: absolute;
}
.padded {
  padding: 5px;
}
</style>
