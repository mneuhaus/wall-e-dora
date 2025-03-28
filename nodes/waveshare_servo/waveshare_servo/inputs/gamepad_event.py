from typing import Dict, Any, Optional

# --- Main Event Handler ---

def handle_gamepad_event(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Handle gamepad button and axis events and map them to servo movements.
    Handles potential differences in input ranges (e.g., 0-1 vs -1 to 1)
    via an optional 'input_range' field in servo gamepad_config.

    Args:
        event: The event data containing control name ('id') and value.
        context: The node context containing servos and other state.
               It is assumed that a 'move_servo(context, servo_id, position)'
               function is available or callable within this execution environment.
    """
    control_name = event.get("id")
    raw_value = event.get("value")

    if control_name is None:
        print(f"[GAMEPAD] Invalid gamepad event (no control name 'id'): {event}")
        return

    # --- Robust Value Extraction ---
    value = None
    try:
        # Handle PyArrow arrays (most common case from dataflow)
        if hasattr(raw_value, "__len__") and len(raw_value) > 0:
            item = raw_value[0]
            if hasattr(item, "as_py"): value = item.as_py()
            else: value = float(str(item).strip('"\'')) # Attempt conversion
        elif isinstance(raw_value, (int, float)): value = float(raw_value)
        elif isinstance(raw_value, str): value = float(raw_value.strip())
        else: value = 0.0 # Default for None or unexpected types

    except (ValueError, TypeError) as e:
        print(f"[GAMEPAD] Warning: Could not convert raw value '{raw_value}' to number for control '{control_name}'. Error: {e}. Using 0.0.")
        value = 0.0
    except Exception as e:
        print(f"[GAMEPAD] Error extracting value for control '{control_name}': {e}. Using 0.0.")
        value = 0.0

    # Ensure value is float for consistency downstream
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        print(f"[GAMEPAD] Critical Error: Could not ensure final value is float for control '{control_name}'. Value: {value}. Aborting handling.")
        return

    # --- Find Mapped Servos ---
    mapped_servos = find_servos_by_control(control_name, context)
    if not mapped_servos: return

    # --- Process Each Mapped Servo ---
    for servo in mapped_servos:
        try:
            servo_id = servo.id
            if not hasattr(servo, 'settings') or not hasattr(servo.settings, 'gamepad_config'):
                print(f"[GAMEPAD] Servo {servo_id} mapped to '{control_name}' but missing settings or gamepad_config.")
                continue

            config = servo.settings.gamepad_config
            if not config: # Check if config is not None or empty dict
                 print(f"[GAMEPAD] Servo {servo_id} mapped to '{control_name}' but has empty gamepad_config.")
                 continue

            # control_type is more about HOW the servo behaves (button/axis action)
            # input_range (new) is about the EXPECTED VALUE RANGE from the device
            control_type = config.get("type")
            input_range = config.get("input_range") # NEW: Expect "unipolar" (0-1) or "bipolar" (-1 to 1)

            # Calculate servo position based on mapping configuration
            position = calculate_position(servo, value, context, control_name, control_type, input_range) # Pass input_range

            if position is not None:
                min_pulse = getattr(getattr(servo, 'settings', None), 'min_pulse', 0)
                max_pulse = getattr(getattr(servo, 'settings', None), 'max_pulse', 1023)
                # Ensure position is int before clamping
                clamped_position = max(min_pulse, min(int(round(position)), max_pulse)) # Round before int conversion

                current_pos = getattr(getattr(servo, 'settings', None), 'position', None)
                if current_pos is None or clamped_position != current_pos:
                     print(f"[GAMEPAD] Moving servo {servo_id} to position {clamped_position} (Control: '{control_name}', Value: {value:.2f}, Raw Calc: {position:.2f})")
                     from waveshare_servo.inputs.move_servo import move_servo
                     move_servo(context, servo_id, clamped_position)
                     # Update context state AFTER successful move
                     if "servos" in context and servo_id in context["servos"]:
                        try: context["servos"][servo_id].settings.position = clamped_position
                        except AttributeError: pass # Ignore if context structure is different

        except AttributeError as e:
             print(f"[GAMEPAD] Error processing servo: Missing attribute {e}. Servo data: {getattr(servo, '__dict__', 'N/A')}")
        except ImportError:
             print(f"[GAMEPAD] CRITICAL ERROR: Could not import 'move_servo' function.")
             break
        except Exception as e:
             print(f"[GAMEPAD] Unexpected error processing servo {getattr(servo, 'id', 'UNKNOWN')}: {e}")


def find_servos_by_control(control_name: str, context: Dict[str, Any]) -> list:
    """ Finds servos mapped to a specific control. (No changes needed here) """
    servos = context.get("servos", {})
    matched_servos = []
    for servo in servos.values():
        try:
            if hasattr(servo, 'settings') and getattr(servo.settings, 'attached_control', None) == control_name:
                 matched_servos.append(servo)
        except Exception as e:
            print(f"[GAMEPAD:FIND] Error accessing settings for a servo: {e}")
    return matched_servos


def calculate_position(servo, value: float, context: Dict[str, Any], control_name: str, control_type: Optional[str], input_range: Optional[str]) -> Optional[float]: # Return float for precision before clamping
    """
    Calculate servo position based on control value, configuration, and input range.

    Args:
        servo: The servo object.
        value: The processed gamepad control value (float).
        context: The node context.
        control_name: The name of the gamepad control.
        control_type: Configured type ("button" or "axis").
        input_range: Configured input range ("unipolar", "bipolar", or None).

    Returns:
        The calculated position (float) or None.
    """
    try:
        config = servo.settings.gamepad_config
        if not config: return None

        mode = config.get("mode")
        invert = config.get("invert", False)
        multiplier = float(config.get("multiplier", 1.0))
        is_analog_override = config.get("isAnalog", False) # If type=button, treat as analog anyway

        # --- Determine Effective Input Range (Defaulting for Android target) ---
        effective_input_range = input_range
        if effective_input_range is None:
             # If not specified, guess based on type, defaulting to UNIPOLAR for Android focus
             if control_type == "axis":
                  effective_input_range = "bipolar" # Traditional joysticks often are
                  print(f"[GAMEPAD:CALC] Warning: 'input_range' not set for axis '{control_name}' ({servo.id}). Assuming 'bipolar' (-1 to 1). Specify if input is 'unipolar' (0 to 1).")
             else: # button or unknown
                  effective_input_range = "unipolar" # Safer default for triggers/buttons on Android
                  # Only warn if it's likely being treated as analog later
                  if mode in ["absolute", "relative"] or is_analog_override:
                      print(f"[GAMEPAD:CALC] Warning: 'input_range' not set for control '{control_name}' ({servo.id}) acting as analog. Assuming 'unipolar' (0 to 1). Specify if input is 'bipolar' (-1 to 1).")


        # --- Apply Inversion based on effective range ---
        original_value = value
        if invert:
            if effective_input_range == "bipolar":
                 value = -value # Flip sign for -1 to 1
            elif effective_input_range == "unipolar":
                 value = 1.0 - value # Map 0->1, 1->0
            else: # Fallback guess - unipolar inversion is often safer
                 value = 1.0 - value
                 print(f"[GAMEPAD:CALC] Warning: Inverting with unknown input_range for {control_name} ({servo.id}). Assuming unipolar inversion (1.0 - value).")
            # print(f"[GAMEPAD] Inverted value ({effective_input_range}) for {control_name} ({servo.id}): {original_value:.2f} -> {value:.2f}")


        # --- Determine Handling Path ---
        # Treat as axis if type is axis OR (type is button AND mode is absolute/relative OR isAnalog override)
        is_handled_as_axis = (
            control_type == "axis" or
            (control_type == "button" and (mode in ["absolute", "relative"] or is_analog_override))
        )

        if is_handled_as_axis:
            # print(f"[GAMEPAD] Handling '{control_name}' ({servo.id}) as ANALOG (Mode: {mode}, Input: {effective_input_range})")
            # Pass the *determined* effective_input_range for correct processing
            return handle_axis_control(servo, value, mode, multiplier, context, effective_input_range)
        elif control_type == "button":
            # print(f"[GAMEPAD] Handling '{control_name}' ({servo.id}) as BUTTON (Mode: {mode})")
            # Button handler expects 0/1 logic, value should be raw (but possibly inverted)
            return handle_button_control(servo, value, mode, context)
        else:
            print(f"[GAMEPAD] Unknown control type '{control_type}' for control '{control_name}' ({servo.id}).")
            return None

    except AttributeError as e:
        print(f"[GAMEPAD:CALC] Error accessing servo attributes for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None
    except Exception as e:
        print(f"[GAMEPAD:CALC] Error calculating position for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None


def handle_button_control(servo, value: float, mode: Optional[str], context: Dict[str, Any]) -> Optional[int]:
    """ Handle button-type controls (toggle or momentary). Assumes 0/1 logic via threshold. """
    try:
        # Use a threshold suitable for 0-1 inputs (analog triggers acting as buttons)
        # and also works for digital 0/1 inputs.
        threshold = 0.5
        is_pressed = value > threshold
        button_state = 1 if is_pressed else 0

        # State tracking remains the same
        button_states = context.setdefault("gamepad_button_states", {})
        servo_id = servo.id
        state_key = f"{servo_id}"
        prev_state = button_states.get(state_key, 0)

        new_position = None
        min_pulse = servo.settings.min_pulse
        max_pulse = servo.settings.max_pulse

        if mode == "toggle":
            if button_state == 1 and prev_state == 0: # Trigger on press edge
                current_pos = servo.settings.position # Assumes position is reliably updated
                middle_point = min_pulse + (max_pulse - min_pulse) / 2.0
                new_position = min_pulse if current_pos > middle_point else max_pulse
        elif mode == "momentary":
             new_position = max_pulse if button_state == 1 else min_pulse
        else:
            print(f"[GAMEPAD:BUTTON] Unknown button mode '{mode}' for servo {servo_id}")

        button_states[state_key] = button_state
        return new_position # Return int as button modes usually target endpoints

    except AttributeError as e:
        print(f"[GAMEPAD:BUTTON] Error accessing servo attributes for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None
    except Exception as e:
        print(f"[GAMEPAD:BUTTON] Error handling button control for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None


def handle_axis_control(servo, value: float, mode: Optional[str], multiplier: float, context: Dict[str, Any], input_range: str) -> Optional[float]: # Return float
    """
    Handle axis-type controls (absolute or relative) respecting the input_range.
    """
    try:
        min_pulse = float(servo.settings.min_pulse) # Ensure float for calculations
        max_pulse = float(servo.settings.max_pulse)
        servo_range = max_pulse - min_pulse
        if servo_range <= 0: return None # Invalid range

        new_position = None

        if mode == "absolute":
            normalized_value = 0.0 # Target range [0.0, 1.0]

            if input_range == "bipolar":
                 # Input: -1.0 to 1.0
                 clamped_value = max(-1.0, min(value, 1.0))
                 normalized_value = (clamped_value + 1.0) / 2.0 # Map [-1, 1] -> [0, 1]
                 # print(f"[GAMEPAD:AXIS] Absolute (Bipolar): Servo {servo.id}, Val={value:.2f} -> Norm={normalized_value:.2f}")
            elif input_range == "unipolar":
                 # Input: 0.0 to 1.0 (like Android trigger)
                 clamped_value = max(0.0, min(value, 1.0))
                 normalized_value = clamped_value # Already in [0, 1] range
                 # print(f"[GAMEPAD:AXIS] Absolute (Unipolar): Servo {servo.id}, Val={value:.2f} -> Norm={normalized_value:.2f}")
            else: # Should not happen if calculate_position sets a default
                 print(f"[GAMEPAD:AXIS] Error: Reached absolute mode with unknown input_range '{input_range}' for {servo.id}")
                 return None

            # Apply multiplier for sensitivity/scaling within the [0, 1] space
            center_point = 0.5
            effective_value = center_point + (normalized_value - center_point) * multiplier
            final_scaled_value = max(0.0, min(effective_value, 1.0))

            new_position = min_pulse + (final_scaled_value * servo_range)
            # print(f"[GAMEPAD:AXIS] Absolute Output: Servo {servo.id} -> Scaled={final_scaled_value:.2f} -> Pos={new_position:.1f}")


        elif mode == "relative":
            deadzone = 0.1
            if abs(value) > deadzone:
                # Determine rate based on input range
                relative_rate = 0.0
                if input_range == "bipolar":
                    # Expects -1 to 1 for direction/speed
                    relative_rate = max(-1.0, min(value, 1.0))
                elif input_range == "unipolar":
                    # Expects 0 to 1 for speed (direction comes from invert/multiplier sign)
                    # Assume 0 is stop, 1 is max rate *in the configured direction*
                    relative_rate = max(0.0, min(value, 1.0))
                    # If multiplier is negative, rate effectively becomes negative for change calc
                else: return None # Should not happen

                base_step_per_event = servo_range * 0.02 # % step per event
                change = relative_rate * multiplier * base_step_per_event

                current_pos = float(servo.settings.position) # Need reliable current pos
                target_pos = current_pos + change
                new_position = max(min_pulse, min(target_pos, max_pulse)) # Clamp result
                # print(f"[GAMEPAD:AXIS] Relative ({input_range}): Servo {servo.id}, Val={value:.2f}, Rate={relative_rate:.2f}, Change={change:.1f}, New={new_position:.1f}")
            # else: stay at current position (new_position remains None implicitly if not set)

        else:
            print(f"[GAMEPAD:AXIS] Unknown axis mode '{mode}' for servo {servo.id}")

        return new_position # Return float

    except AttributeError as e:
        print(f"[GAMEPAD:AXIS] Error accessing servo attributes for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None
    except Exception as e:
        print(f"[GAMEPAD:AXIS] Error handling axis control for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None