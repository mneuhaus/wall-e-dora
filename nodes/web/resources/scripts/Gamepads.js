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
    this.customMapping = null;
    this.isMapping = false; // Flag to indicate mapping is in progress

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

    // Set up listener for profiles list updates
    node.on('gamepad_profiles_list', (event) => {
      if (!event || !event.value) return;
      
      // The server will now send the full profile data, not just names
      const profiles = event.value;
      
      // Try to find matching profile by ID first
      if (profiles[this.id]) {
        const profile = profiles[this.id];
        console.log('Found profile for this gamepad by ID:', profile.name);
        
        if (profile.mapping) {
          // Apply mapping from profile
          
          this.customMapping = {
            gamepad_id: this.id,
            name: profile.name,
            mapping: profile.mapping
          };
          console.log('Applied mapping from profile:', profile.name);
          
          // Force update all listeners to ensure UI refresh
          this._forceUpdateHandlers.forEach(handler => handler());
          return;
        }
      }
      
      // If no direct match, try by vendor/product IDs
      try {
        const vendorMatch = this.id.match(/Vendor:\s*([0-9a-fA-F]+)/);
        const productMatch = this.id.match(/Product:\s*([0-9a-fA-F]+)/);
        
        if (vendorMatch && productMatch) {
          const vendorId = vendorMatch[1].trim().toLowerCase();
          const productId = productMatch[1].trim().toLowerCase();
          
          // Look for a matching profile by vendor+product
          for (const [id, profile] of Object.entries(profiles)) {
            if (profile.vendorId && profile.productId && 
                profile.vendorId.toLowerCase() === vendorId && 
                profile.productId.toLowerCase() === productId &&
                profile.mapping) {
              
              console.log(`Found profile by vendor:${vendorId}/product:${productId} - ${profile.name}`);
              
              this.customMapping = {
                gamepad_id: this.id,
                name: profile.name,
                mapping: profile.mapping
              };
              console.log('Applied mapping from profile:', profile.name);
              
              // Force update all listeners to ensure UI refresh
              this._forceUpdateHandlers.forEach(handler => handler());
              return;
            }
          }
        }
      } catch (e) {
        console.error('Error checking for profile match by vendor/product:', e);
      }
    });
    
    // Keep this for backward compatibility
    node.on('gamepad_profile', (event) => {
      if (event && event.value && event.value.gamepad_id === this.id) {
        this.customMapping = event.value;
        console.log('Loaded custom gamepad mapping via direct response:', this.customMapping);
        
        // Force update all listeners to ensure UI refresh
        this._forceUpdateHandlers.forEach(handler => handler());
      }
    });

    // Load custom mapping if available
    this.loadCustomMapping();

    // Start polling
    this.pollIntervalId = setInterval(() => {
      this.updateState();
    }, 16); // 16ms for 60Hz polling (more responsive updates)
  }

  updateState() {
    const gamepad = navigator.getGamepads()[this.index];
    if (!gamepad) return;

    // Track previous states for axis correlation detection
    if (!this._prevButtonState) {
      this._prevButtonState = {};
      this._prevAxesState = {};
    }

    // Special debug for button 9 (raw from gamepad API)
    if (gamepad.buttons && gamepad.buttons[9]) {
      const button9Value = gamepad.buttons[9].value;
      const button9Changed = this._prevButtonState.button9 !== button9Value;
      
      // Always log button 9 value when it changes
      if (button9Changed) {
        console.log(`BUTTON 9 CHANGED: ${this._prevButtonState.button9} → ${button9Value}`);
        
        // Check for specific axes commonly associated with triggers (5 is common for right trigger)
        const potentialTriggerAxes = [4, 5, 6, 7]; // Common axes for triggers
        
        potentialTriggerAxes.forEach(axisIndex => {
          if (gamepad.axes && gamepad.axes[axisIndex] !== undefined) {
            console.log(`  Potential trigger axis ${axisIndex}: ${gamepad.axes[axisIndex]}`);
          }
        });
      }
      
      // Only do detailed logging when button is pressed or changing
      if (button9Value > 0 || button9Changed) {
        // Log all axes with non-trivial values
        if (gamepad.axes) {
          let significantChanges = [];
          
          gamepad.axes.forEach((value, index) => {
            const prevValue = this._prevAxesState[`axis${index}`] || 0;
            const change = Math.abs(value - prevValue);
            
            // Detect axes that change in correlation with button 9
            if (button9Changed && change > 0.01) {
              significantChanges.push(`Axis ${index} changed by ${change.toFixed(4)} when button 9 changed by ${Math.abs(button9Value - (this._prevButtonState.button9 || 0)).toFixed(4)}`);
            }
            
            // Update previous value
            this._prevAxesState[`axis${index}`] = value;
          });
          
          // Log any axes that changed in correlation with button 9
          if (significantChanges.length > 0) {
            console.log(`CORRELATED CHANGES WITH BUTTON 9:`);
            significantChanges.forEach(msg => console.log(`  ${msg}`));
          }
        }
      }
      
      // Save the current button 9 state for next comparison
      this._prevButtonState.button9 = button9Value;
    }

    let hasChanges = false;

    // If using a custom mapping, apply it
    if (this.customMapping) {
      this.applyCustomMapping(gamepad);
      return;
    }

    // Default mapping logic
    // Update button values
    Object.keys(this.buttons).forEach((index) => {
      if (!this.buttons[index] || !gamepad.buttons[parseInt(index)]) return;
      
      // Get the actual button from the gamepad
      const buttonIndex = parseInt(index);
      const gamepadButton = gamepad.buttons[buttonIndex];
      
      // Skip non-control properties
      
      if(index == 6 || index == 7) {
        // Analog triggers (L2/R2)
        const newValue = parseFloat(gamepadButton.value).toFixed(4);
        
        if (this[this.buttons[index]].value != newValue) {
          this[this.buttons[index]].value = newValue;
          
          node.emit('GAMEPAD_' + this.buttons[index], [gamepadButton.value]);
          hasChanges = true;
        }
      } else {
        // Regular buttons - check if we're converting what should be analog values
        // Check if this button has interesting values that suggest it's really analog
        const hasDecimalValue = gamepadButton.value > 0 && gamepadButton.value < 1;
        
        if (hasDecimalValue) {
          console.log(`FOUND ANALOG BUTTON: ${this.buttons[index]} (index: ${index}) value: ${gamepadButton.value}`);
          // Process as an analog button
          const newValue = parseFloat(gamepadButton.value).toFixed(4);
          if (this[this.buttons[index]].value != newValue) {
            this[this.buttons[index]].value = newValue;
            node.emit('GAMEPAD_' + this.buttons[index], [gamepadButton.value]);
            hasChanges = true;
          }
        } else {
          // Process as a digital button (0 or 1)
          const newValue = gamepadButton.value ? 1 : 0;
          if (this[this.buttons[index]].value != newValue) {
            // Log when buttons are pressed (but not released to avoid spam)
            if (newValue === 1) {
              console.log(`BUTTON PRESS DETECTED: ${this.buttons[index]} (raw value: ${gamepadButton.value})`);
            
              // Dispatch a DOM event for redundancy
              const buttonPressEvent = new CustomEvent(`GAMEPAD_${this.buttons[index]}`, {
                detail: { value: newValue }
              });
              window.dispatchEvent(buttonPressEvent);
              
              // Flash visual effect for UI elements
              const flashEvent = new CustomEvent('gamepad_button_flash', {
                detail: { control: this.buttons[index], type: 'button', index: parseInt(index) }
              });
              window.dispatchEvent(flashEvent);
            }
            
            this[this.buttons[index]].value = newValue;
            
            // Only emit events if not in mapping mode
            if (!this.isMapping) {
              node.emit('GAMEPAD_' + this.buttons[index], [newValue]);
            }
            
            hasChanges = true;
          }
        }
      }
    });

    // Update axis values
    Object.keys(this.axes).forEach((index) => {
      if (!this.axes[index] || gamepad.axes[parseInt(index)] === undefined) return;
      
      const newValue = parseFloat(gamepad.axes[parseInt(index)]).toFixed(4);
      if (this[this.axes[index]].value != newValue) {
        this[this.axes[index]].value = newValue;
        
        // Only emit events if not in mapping mode
        if (!this.isMapping) {
          node.emit('GAMEPAD_' + this.axes[index], [gamepad.axes[parseInt(index)]]);
        }
        
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

  // Apply custom mapping to the gamepad
  applyCustomMapping(gamepad) {
    if (!this.customMapping || !gamepad) return;
    
    let hasChanges = false;
    const mapping = this.customMapping.mapping;
    
    // Process gamepad mapping
    
    // Process each control in the standard mapping
    Object.keys(mapping).forEach(controlName => {
      const mappedInput = mapping[controlName];
      if (!mappedInput) return;
      
      let newValue = 0;
      
      // Get the input value based on the mapped type (button or axis)
      if (mappedInput.type === 'button' && gamepad.buttons[mappedInput.index]) {
        // Get the raw input value and button properties
        const gamepadButton = gamepad.buttons[mappedInput.index];
        const rawValue = gamepadButton.value;
        
        // Use the isAnalog flag to determine how to handle button values
        if (mappedInput.isAnalog) {
          // For analog buttons (like triggers), preserve the full range of values
          newValue = parseFloat(rawValue).toFixed(4);
        } else {
          // For digital buttons, use binary 0/1 values
          newValue = rawValue ? 1 : 0;
        }
      } else if (mappedInput.type === 'axis' && gamepad.axes[mappedInput.index] !== undefined) {
        // Axes are always analog
        const rawValue = gamepad.axes[mappedInput.index];
        newValue = parseFloat(rawValue).toFixed(4);
      } else {
        return; // Skip if input not found
      }
      
      // Update the control value if it changed
      if (this[controlName] && this[controlName].value != newValue) {
        // Track changes
        this[controlName].value = newValue;
        
        // Emit event for button press (when pressed, not released)
        if (mappedInput.type === 'button' && newValue === 1) {
          console.log(`MAPPED BUTTON PRESS: ${controlName} (raw index: ${mappedInput.index})`);
          
          // Dispatch DOM event for redundancy (even during mapping for UI updates)
          const buttonPressEvent = new CustomEvent(`GAMEPAD_${controlName}`, {
            detail: { value: newValue }
          });
          window.dispatchEvent(buttonPressEvent);
          
          // Flash visual effect for UI elements (even during mapping)
          const flashEvent = new CustomEvent('gamepad_button_flash', {
            detail: { control: controlName, type: 'button', index: mappedInput.index }
          });
          window.dispatchEvent(flashEvent);
        }
        
        // Only emit system events if not in mapping mode
        if (!this.isMapping) {
          // Emit the control event to the system
          node.emit('GAMEPAD_' + controlName, [newValue]);
        }
        
        hasChanges = true;
      }
    });
    
    // Notify subscribers of changes
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

  // Get custom mapping from the profiles list
  loadCustomMapping() {
    // Just log that we're waiting for the mapping
    // The mapping will come automatically from the tick event
    console.log('Waiting for profiles list to include mapping for:', this.id);
    // No request needed - tick will send the profiles
  }

  // Register a function to be called when gamepad data changes
  registerForceUpdate(handler) {
    this._forceUpdateHandlers.add(handler);
    return () => {
      this._forceUpdateHandlers.delete(handler);
    };
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
