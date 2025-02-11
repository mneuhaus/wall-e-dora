<script setup>
import { useTemplateRef, ref, onMounted, onUnmounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import gamepads from '../Gamepads';

const route = useRoute();
const gamepad = ref(gamepads.gamepads[route.params.index] ? gamepads.gamepads[route.params.index] : null);

gamepads.on('gamepadconnected', () => {
  gamepad.value = gamepads.gamepads[route.params.index];
})

</script>

<style type="text/css" scoped>
  h5 {
    margin-bottom: 20px;
  }
</style>

<template>
  <div class="controller" style="margin: 20px;" v-if="gamepad">
    <div v-if="gamepad">
        <h6>{{gamepad.id}}</h6>
        <div class="grid">
            <div class="s4">
                <table class="stripes">
                  <tbody>
                    <tr>
                        <th>LEFT_ANALOG_STICK X</th><td>{{gamepad.LEFT_ANALOG_STICK_X}}</td>
                    </tr>
                    <tr>
                        <th>LEFT_ANALOG_STICK Y</th><td>{{gamepad.LEFT_ANALOG_STICK_Y}}</td>
                    </tr>
                    <tr>
                        <th>RIGHT_ANALOG_STICK X</th><td>{{gamepad.RIGHT_ANALOG_STICK_X}}</td>
                    </tr>
                    <tr>
                        <th>RIGHT_ANALOG_STICK Y</th><td>{{gamepad.RIGHT_ANALOG_STICK_Y}}</td>
                    </tr>
                    <tr>
                        <th>DPAD_UP</th><td>{{gamepad.DPAD_UP}}</td>
                    </tr>
                    <tr>
                        <th>DPAD_DOWN</th><td>{{gamepad.DPAD_DOWN}}</td>
                    </tr>
                    <tr>
                        <th>DPAD_LEFT</th><td>{{gamepad.DPAD_LEFT}}</td>
                    </tr>
                    <tr>
                        <th>DPAD_RIGHT</th><td>{{gamepad.DPAD_RIGHT}}</td>
                    </tr>
                  </tbody>
                </table>
            </div>
            <div class="s4">
                <table class="stripes">
                  <tbody>
                    <tr>
                        <th>FACE_1</th><td>{{gamepad.FACE_1}}</td>
                    </tr>
                    <tr>
                        <th>FACE_2</th><td>{{gamepad.FACE_2}}</td>
                    </tr>
                    <tr>
                        <th>FACE_3</th><td>{{gamepad.FACE_3}}</td>
                    </tr>
                    <tr>
                        <th>FACE_4</th><td>{{gamepad.FACE_4}}</td>
                    </tr>
                    <tr>
                        <th>LEFT_SHOULDER</th><td>{{gamepad.LEFT_SHOULDER}}</td>
                    </tr>
                    <tr>
                        <th>RIGHT_SHOULDER</th><td>{{gamepad.RIGHT_SHOULDER}}</td>
                    </tr>
                    <tr>
                        <th>LEFT_SHOULDER_BOTTOM</th><td>{{gamepad.LEFT_SHOULDER_BOTTOM}}</td>
                    </tr>
                    <tr>
                        <th>RIGHT_SHOULDER_BOTTOM</th><td>{{gamepad.RIGHT_SHOULDER_BOTTOM}}</td>
                    </tr>
                  </tbody>
                </table>
            </div>
            <div class="s4">
                <table class="stripes">
                  <tbody>
                    <tr>
                        <th>SELECT</th><td>{{gamepad.SELECT}}</td>
                    </tr>
                    <tr>
                        <th>START</th><td>{{gamepad.START}}</td>
                    </tr>
                    <tr>
                        <th>LEFT_ANALOG_BUTTON</th><td>{{gamepad.LEFT_ANALOG_BUTTON}}</td>
                    </tr>
                    <tr>
                        <th>RIGHT_ANALOG_BUTTON</th><td>{{gamepad.RIGHT_ANALOG_BUTTON}}</td>
                    </tr>
                    <tr>
                        <th>HOME</th><td>{{gamepad.HOME}}</td>
                    </tr>
                    <tr>
                        <th>MISCBUTTON_1</th><td>{{gamepad.MISCBUTTON_1}}</td>
                    </tr>
                    <tr>
                        <th>MISCBUTTON_2</th><td>{{gamepad.MISCBUTTON_2}}</td>
                    </tr>
                  </tbody>
                </table>
            </div>
        </div>
    </div>
  </div>
</template>