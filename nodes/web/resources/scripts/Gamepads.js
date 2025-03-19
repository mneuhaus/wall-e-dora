import mitt from 'mitt';
import node from './Node.js';

class Gamepad {
  constructor(gamepadApi) {
    this.id = gamepadApi.id;
    this.index = gamepadApi.index;
    this.api = gamepadApi;
    this.emitter = mitt();

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

    // Initialize values without Vue reactivity
    Object.keys(this.axes).forEach((index) => {
      this[this.axes[index]] = { value: 0 };
    });
    
    Object.keys(this.buttons).forEach((index) => {
      this[this.buttons[index]] = { value: 0 };
    });

    // Start polling
    this.pollIntervalId = setInterval(() => {
      let gamepad = navigator.getGamepads()[this.index];
      if (!gamepad) return;

      let hasChanges = false;

      Object.keys(this.buttons).forEach((index) => {
        if (!this.buttons[index] || !gamepad.buttons[index]) return;
        
        if(index == 6 || index == 7) {
          // Analog triggers (L2/R2)
          const newValue = parseFloat(gamepad.buttons[index].value).toFixed(4);
          if (this[this.buttons[index]].value != newValue) {
            this[this.buttons[index]].value = newValue;
            node.emit('GAMEPAD_' + this.buttons[index], [gamepad.buttons[index].value]);
            hasChanges = true;
          }
        } else {
          // Regular buttons
          if (this[this.buttons[index]].value != gamepad.buttons[index].value) {
            this[this.buttons[index]].value = gamepad.buttons[index].value;
            node.emit('GAMEPAD_' + this.buttons[index], [gamepad.buttons[index].value]);
            hasChanges = true;
          }
        }
      });

      Object.keys(this.axes).forEach((index) => {
        if (!this.axes[index] || gamepad.axes[index] === undefined) return;
        
        const newValue = parseFloat(gamepad.axes[index]).toFixed(4);
        if (this[this.axes[index]].value != newValue) {
          this[this.axes[index]].value = newValue;
          node.emit('GAMEPAD_' + this.axes[index], [gamepad.axes[index]]);
          hasChanges = true;
        }
      });

      // Emit a general update event if any values changed
      if (hasChanges) {
        this.emitter.emit('gamepad_update', this);
      }
    }, 50); // Increased frequency for more responsive updates
  }

  on(eventName, callback) {
    return this.emitter.on(eventName, callback);
  }

  off(eventName, callback) {
    return this.emitter.off(eventName, callback);
  }

  dispose() {
    clearInterval(this.pollIntervalId);
    this.emitter.all.clear();
  }
}

class Gamepads {
  constructor() {
    this.gamepads = [];
    this.emitter = mitt();

    window.addEventListener("gamepadconnected", (event) => {
      console.log("Gamepad connected:", event);
      if (this.gamepads[event.gamepad.index]) {
        // Clean up existing gamepad instance if there was one
        this.gamepads[event.gamepad.index].dispose();
      }
      this.gamepads[event.gamepad.index] = new Gamepad(event.gamepad);
      this.emitter.emit('gamepadconnected', this.gamepads[event.gamepad.index]);
    });

    window.addEventListener("gamepaddisconnected", (event) => {
      console.log("Lost connection with the gamepad.", event);
      if (this.gamepads[event.gamepad.index]) {
        this.gamepads[event.gamepad.index].dispose();
      }
      this.emitter.emit('gamepaddisconnected', event);
      delete this.gamepads[event.gamepad.index];
    });
  }

  on(eventName, callback) {
    return this.emitter.on(eventName, callback);
  }

  off(eventName, callback) {
    return this.emitter.off(eventName, callback);
  }
}

const gamepads = new Gamepads();

export default gamepads;