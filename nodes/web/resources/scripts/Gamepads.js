import mitt from 'mitt';
import node from './Node.js';

class Gamepad {
  constructor(gamepadApi) {
    this.id = gamepadApi.id;
    this.index = gamepadApi.index;
    this.api = gamepadApi;
    this.emitter = mitt();
    this._forceUpdateHandlers = new Set();
    this.servoMapping = {};

    // Log gamepad details for debugging
    console.log('Gamepad connected:', {
      id: gamepadApi.id,
      index: gamepadApi.index,
      axes: gamepadApi.axes.length,
      buttons: gamepadApi.buttons.length
    });

    // Default mappings
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

    // Initialize values
    Object.keys(this.axes).forEach((index) => {
      this[this.axes[index]] = { value: 0 };
    });
    
    Object.keys(this.buttons).forEach((index) => {
      this[this.buttons[index]] = { value: 0 };
    });

    // Start polling
    this.pollIntervalId = setInterval(() => {
      this.updateState();
    }, 50); // 50ms for responsive updates
  }

  updateState() {
    const gamepad = navigator.getGamepads()[this.index];
    if (!gamepad) return;

    let hasChanges = false;

    // Debug output for raw gamepad values 
    if (Math.random() < 0.01) { // Only log occasionally to avoid console spam
      console.log('Raw Gamepad Values:', {
        axes: Array.from(gamepad.axes).map(v => parseFloat(v).toFixed(4)),
        buttons: Array.from(gamepad.buttons).map((b, i) => ({
          index: i,
          value: parseFloat(b.value).toFixed(4),
          pressed: b.pressed
        })).filter(b => b.value > 0 || b.pressed)
      });
    }

    // Update button values
    Object.keys(this.buttons).forEach((index) => {
      if (!this.buttons[index] || !gamepad.buttons[parseInt(index)]) return;
      
      if(index == 6 || index == 7) {
        // Analog triggers (L2/R2)
        const newValue = parseFloat(gamepad.buttons[parseInt(index)].value).toFixed(4);
        if (this[this.buttons[index]].value != newValue) {
          this[this.buttons[index]].value = newValue;
          node.emit('GAMEPAD_' + this.buttons[index], [gamepad.buttons[parseInt(index)].value]);
          hasChanges = true;
        }
      } else {
        // Regular buttons
        const newValue = gamepad.buttons[parseInt(index)].value ? 1 : 0;
        if (this[this.buttons[index]].value != newValue) {
          this[this.buttons[index]].value = newValue;
          node.emit('GAMEPAD_' + this.buttons[index], [newValue]);
          hasChanges = true;
        }
      }
    });

    // Update axis values
    Object.keys(this.axes).forEach((index) => {
      if (!this.axes[index] || gamepad.axes[parseInt(index)] === undefined) return;
      
      const newValue = parseFloat(gamepad.axes[parseInt(index)]).toFixed(4);
      if (this[this.axes[index]].value != newValue) {
        this[this.axes[index]].value = newValue;
        node.emit('GAMEPAD_' + this.axes[index], [gamepad.axes[parseInt(index)]]);
        hasChanges = true;
      }
    });

    // If any values changed, notify subscribers
    if (hasChanges) {
      this.emitter.emit('gamepad_update', this);
      
      // Call any registered force update handlers
      this._forceUpdateHandlers.forEach(handler => {
        if (typeof handler === 'function') {
          handler();
        }
      });
    }
  }

  // Register a function to be called when gamepad data changes
  registerForceUpdate(handler) {
    this._forceUpdateHandlers.add(handler);
    return () => this._forceUpdateHandlers.delete(handler);
  }

  on(eventName, callback) {
    return this.emitter.on(eventName, callback);
  }

  off(eventName, callback) {
    return this.emitter.off(eventName, callback);
  }

  dispose() {
    clearInterval(this.pollIntervalId);
    this._forceUpdateHandlers.clear();
    this.emitter.all.clear();
  }
}

class Gamepads {
  constructor() {
    this.gamepads = [];
    this.emitter = mitt();

    window.addEventListener("gamepadconnected", (event) => {
      console.log("Gamepad connected:", event);
      // Debug log for finding proper gamepad mapping
      console.log("Gamepad details for mapping:", {
        id: event.gamepad.id,
        index: event.gamepad.index, 
        mapping: event.gamepad.mapping,
        axes: {
          count: event.gamepad.axes.length,
          values: Array.from(event.gamepad.axes).map(v => parseFloat(v).toFixed(4))
        },
        buttons: {
          count: event.gamepad.buttons.length,
          values: Array.from(event.gamepad.buttons).map((b, i) => ({
            index: i,
            value: parseFloat(b.value).toFixed(4),
            pressed: b.pressed
          }))
        }
      });
      
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

  attachServo(servoId, controlType, controlIndex) {
    this.servoMapping[`${controlType}_${controlIndex}`] = servoId;
    console.log(`Attached servo ${servoId} to ${controlType} ${controlIndex}`);
  }
}

const gamepads = new Gamepads();

export default gamepads;
