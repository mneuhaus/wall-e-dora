import mitt from 'mitt';
import { ref } from 'vue';
import node from './Node.js';

class Gamepad {
  constructor(gamepadApi) {
    this.id = gamepadApi.id;
    this.index = gamepadApi.index;
    this.api = gamepadApi;

    this.axes = {
      0: "LEFT_ANALOG_STICK_X",
      1: "LEFT_ANALOG_STICK_Y",
      2: "RIGHT_ANALOG_STICK_X",
      3: "RIGHT_ANALOG_STICK_Y"
    };

    this.buttons = {
      0: "FACE_1",
      1: "FACE_2",
      2: "FACE_3",
      3: "FACE_4",
      4: "LEFT_SHOULDER",
      5: "RIGHT_SHOULDER",
      6: "LEFT_SHOULDER_BOTTOM",
      7: "RIGHT_SHOULDER_BOTTOM",
      8: "SELECT",
      9: "START",
      10: "LEFT_ANALOG_BUTTON",
      11: "RIGHT_ANALOG_BUTTON",
      12: "DPAD_UP",
      13: "DPAD_DOWN",
      14: "DPAD_LEFT",
      15: "DPAD_RIGHT",
      16: "HOME",
      17: "MISCBUTTON_1",
      18: "MISCBUTTON_2"
    };

    Object.keys(this.axes).forEach((index) => {
      this[this.axes[index]] = ref(0);
    })
    Object.keys(this.buttons).forEach((index) => {
      this[this.buttons[index]] = ref(0);
    })

    setInterval(() => {
      let gamepad = navigator.getGamepads()[this.index];
      Object.keys(gamepad.buttons).forEach((index) => {
        if (!this[this.buttons[index]]) {
          console.warn('missing button: ' + index);
          return;
        }
        if(index == 6 || index == 7) {
          if (this[this.buttons[index]].value != parseFloat(gamepad.buttons[index].value).toFixed(4)) {
            this[this.buttons[index]].value = parseFloat(gamepad.buttons[index].value).toFixed(4);
            node.emit('GAMEPAD_' + [this.buttons[index]], [gamepad.buttons[index].value]);
          }
        } else {
          if (this[this.buttons[index]].value != gamepad.buttons[index].value) {
            this[this.buttons[index]].value = gamepad.buttons[index].value;
            node.emit('GAMEPAD_' + [this.buttons[index]], [gamepad.buttons[index].value]);
          }
        }
      });

      Object.keys(gamepad.axes).forEach((index) => {
        if (!this[this.axes[index]]) {
          console.warn('axis button: ' + index);
          return;
        }
        if (this[this.axes[index]].value != parseFloat(gamepad.axes[index]).toFixed(4)) {
          this[this.axes[index]].value = parseFloat(gamepad.axes[index]).toFixed(4);
          node.emit('GAMEPAD_' + [this.axes[index]], [gamepad.axes[index]]);
        }
      });
    }, 100);
  }

  on(eventName, callback) {
    this.emitter.on(eventName, callback);
  }
}

class Gamepads {
  constructor() {
    this.gamepads = [];
    this.emitter = mitt();

    window.addEventListener("gamepadconnected", (event) => {
      console.log("Gamepad connected:", event);
      this.gamepads[event.gamepad.index] = new Gamepad(event.gamepad);
      this.emitter.emit('gamepadconnected', gamepads[event.gamepad.index]);
    });

    window.addEventListener("gamepaddisconnected", (event) => {
      console.log("Lost connection with the gamepad.", event);
      this.emitter.emit('gamepaddisconnected', event);
    });
  }

  on(eventName, callback) {
    this.emitter.on(eventName, callback);
  }
}

let gamepads = new Gamepads();

export default gamepads;
