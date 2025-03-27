from typing import Dict, Any, Optional

# --- Main Event Handler ---

def handle_gamepad_event(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Handle gamepad button and axis events and map them to servo movements.

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
            # Use as_py() if available (best method)
            if hasattr(item, "as_py"):
                value = item.as_py()
            # Try string conversion as fallback for Arrow objects
            else:
                raw_str = str(item).strip('"\'')
                try:
                    value = float(raw_str)
                except (ValueError, TypeError):
                    print(f"[GAMEPAD] Warning: Could not convert Arrow item '{raw_str}' to number for control '{control_name}'. Using 0.")
                    value = 0.0
        # Handle simple numeric types
        elif isinstance(raw_value, (int, float)):
            value = float(raw_value)
        # Handle string types (attempt conversion)
        elif isinstance(raw_value, str):
            try:
                value = float(raw_value.strip())
            except (ValueError, TypeError):
                print(f"[GAMEPAD] Warning: Could not convert string '{raw_value}' to number for control '{control_name}'. Using 0.")
                value = 0.0
        # Handle None or unexpected types
        else:
            print(f"[GAMEPAD] Warning: Unsupported or null value type '{type(raw_value)}' for control '{control_name}'. Using 0.")
            value = 0.0

    except Exception as e:
        print(f"[GAMEPAD] Error extracting value for control '{control_name}': {e}. Using 0.")
        value = 0.0

    # Ensure value is float for consistency downstream
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        print(f"[GAMEPAD] Critical Error: Could not ensure final value is float for control '{control_name}'. Value: {value}. Aborting handling.")
        return # Cannot proceed without a valid float

    # --- Find Mapped Servos ---
    mapped_servos = find_servos_by_control(control_name, context)

    if not mapped_servos:
        # Reduce noise: only print if you expect a mapping
        # print(f"[GAMEPAD] No servos mapped to control '{control_name}'")
        return

    # print(f"[GAMEPAD] Found {len(mapped_servos)} servo(s) mapped to '{control_name}' with value {value}")

    # --- Process Each Mapped Servo ---
    for servo in mapped_servos:
        try:
            servo_id = servo.id
            config = servo.settings.gamepad_config

            if not config:
                print(f"[GAMEPAD] Servo {servo_id} mapped to '{control_name}' but has no gamepad_config.")
                continue

            control_type = config.get("type") # "button" or "axis"
            control_mode = config.get("mode") # "toggle", "momentary", "absolute", "relative"

            # print(f"[GAMEPAD] Processing servo {servo_id} (Control: '{control_name}', Type: {control_type}, Mode: {control_mode}, Raw Value: {value})")

            # Calculate servo position based on mapping configuration
            # Pass control_name for logging, control_type for logic differentiation
            position = calculate_position(servo, value, context, control_name, control_type)

            if position is not None:
                # Ensure position is within valid bounds (e.g., 0-1023 or servo's specific min/max pulse)
                # Assuming 0-1023 for generic servo nodes, adjust if necessary based on servo capabilities
                min_pulse = getattr(getattr(servo, 'settings', None), 'min_pulse', 0)
                max_pulse = getattr(getattr(servo, 'settings', None), 'max_pulse', 1023)
                clamped_position = max(min_pulse, min(int(position), max_pulse))


                # Only move if the position actually changed (optional optimization)
                current_pos = getattr(getattr(servo, 'settings', None), 'position', None)
                if current_pos is None or clamped_position != current_pos:
                     print(f"[GAMEPAD] Moving servo {servo_id} to position {clamped_position} (Raw calculated: {position})")
                     # *** This is the call to the actual move_servo function ***
                     # Ensure 'move_servo' is correctly imported or available in the execution scope
                     from waveshare_servo.inputs.move_servo import move_servo # Assuming this is the correct import path
                     move_servo(context, servo_id, clamped_position)
                     # Update the position in the context AFTER moving, if necessary for state tracking
                     # This assumes move_servo doesn't update the context itself.
                     if "servos" in context and servo_id in context["servos"]:
                        try:
                           context["servos"][servo_id].settings.position = clamped_position
                        except AttributeError:
                           print(f"[GAMEPAD] Warning: Could not update position state in context for servo {servo_id}")

                # else:
                #     print(f"[GAMEPAD] No position change needed for servo {servo_id} (already at {clamped_position})")

            # else:
            #     print(f"[GAMEPAD] No position calculation result for servo {servo_id}")

        except AttributeError as e:
             print(f"[GAMEPAD] Error processing servo: Missing attribute {e}. Servo data: {getattr(servo, '__dict__', 'N/A')}")
        except ImportError:
             print(f"[GAMEPAD] CRITICAL ERROR: Could not import 'move_servo' function. Check installation and path.")
             # Potentially re-raise or handle this more gracefully depending on application needs
             break # Stop processing more servos if the move function is missing
        except Exception as e:
             print(f"[GAMEPAD] Unexpected error processing servo {getattr(servo, 'id', 'UNKNOWN')}: {e}")


def find_servos_by_control(control_name: str, context: Dict[str, Any]) -> list:
    """
    Find all servos mapped to a specific gamepad control.
    """
    servos = context.get("servos", {})
    matched_servos = []
    for servo in servos.values():
        try:
            # Check if servo has settings and an attached_control
            if hasattr(servo, 'settings') and hasattr(servo.settings, 'attached_control'):
                if servo.settings.attached_control == control_name:
                    matched_servos.append(servo)
        except Exception as e:
            print(f"[GAMEPAD:FIND] Error accessing settings for a servo: {e}")
            continue # Skip problematic servo object

    # Optional: Reduce noise by only printing if matches are found or expected
    # if matched_servos:
    #     servo_ids = [s.id for s in matched_servos if hasattr(s, 'id')]
    #     print(f"[GAMEPAD:FIND] Found {len(matched_servos)} servos for control '{control_name}': {servo_ids}")
    # else:
    #     print(f"[GAMEPAD:FIND] No servos found for control '{control_name}'")

    return matched_servos


def calculate_position(servo, value: float, context: Dict[str, Any], control_name: str, control_type: Optional[str]) -> Optional[int]:
    """
    Calculate servo position based on control value and mapping configuration.

    Args:
        servo: The servo object (should have settings.gamepad_config).
        value: The processed gamepad control value (float).
        context: The node context.
        control_name: The name of the gamepad control being handled.
        control_type: The type from the config ("button", "axis", or None).

    Returns:
        The calculated position (int, typically within servo's min/max pulse) or None.
    """
    try:
        config = servo.settings.gamepad_config
        if not config:
            return None

        mode = config.get("mode")
        invert = config.get("invert", False)
        multiplier = float(config.get("multiplier", 1.0)) # Ensure float
        is_analog_override = config.get("isAnalog", False) # Explicit override

        # --- Apply Inversion ---
        # Inversion logic depends on the *expected* type of control
        original_value = value
        if invert:
            if control_type == "axis": # Assumes bipolar (-1 to 1) range ideally
                 value = -value
                 # print(f"[GAMEPAD] Inverted axis value for {control_name} ({servo.id}): {original_value} -> {value}")
            elif control_type == "button": # Assumes unipolar (0 to 1) range ideally
                 value = 1.0 - value
                 # print(f"[GAMEPAD] Inverted button value for {control_name} ({servo.id}): {original_value} -> {value}")
            else: # Fallback: guess based on value range? Risky. Let's just flip sign.
                 value = -value
                 # print(f"[GAMEPAD] Inverted unknown type value for {control_name} ({servo.id}): {original_value} -> {value}")


        # --- Determine Handling Path ---
        # Use axis handler if:
        # 1. Config type is "axis"
        # 2. Config type is "button" BUT mode is "absolute" or "relative"
        # 3. Config type is "button" BUT isAnalog override is true
        if control_type == "axis" or \
           (control_type == "button" and mode in ["absolute", "relative"]) or \
           (control_type == "button" and is_analog_override):

            # print(f"[GAMEPAD] Handling '{control_name}' ({servo.id}) as ANALOG (Type: {control_type}, Mode: {mode}, isAnalog: {is_analog_override})")
            # Pass the ORIGINAL control_type to handle_axis_control to differentiate input range
            return handle_axis_control(servo, value, mode, multiplier, context, control_type)

        elif control_type == "button":
            # print(f"[GAMEPAD] Handling '{control_name}' ({servo.id}) as BUTTON (Mode: {mode})")
            return handle_button_control(servo, value, mode, context)

        else:
            print(f"[GAMEPAD] Unknown control type '{control_type}' for control '{control_name}' ({servo.id}). Cannot calculate position.")
            return None

    except AttributeError as e:
        print(f"[GAMEPAD:CALC] Error accessing servo attributes for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None
    except Exception as e:
        print(f"[GAMEPAD:CALC] Error calculating position for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None


def handle_button_control(servo, value: float, mode: Optional[str], context: Dict[str, Any]) -> Optional[int]:
    """
    Handle button-type controls (toggle or momentary). Handles 0/1 logic.
    """
    try:
        # Determine if pressed (value > threshold, commonly 0.5 for analog triggers/buttons)
        is_pressed = value > 0.5
        button_state = 1 if is_pressed else 0

        button_states = context.setdefault("gamepad_button_states", {})
        servo_id = servo.id
        state_key = f"{servo_id}" # Use servo ID for state tracking

        # Get previous state, defaulting to 0 (released)
        prev_state = button_states.get(state_key, 0)

        # --- Apply Mode Logic ---
        new_position = None
        min_pulse = servo.settings.min_pulse
        max_pulse = servo.settings.max_pulse

        if mode == "toggle":
            # Toggle only on PRESS event (transition from 0 to 1)
            if button_state == 1 and prev_state == 0:
                current_pos = servo.settings.position
                # Toggle between min and max
                middle_point = min_pulse + (max_pulse - min_pulse) / 2.0
                new_position = min_pulse if current_pos > middle_point else max_pulse
                # print(f"[GAMEPAD:BUTTON] Toggle {servo_id}: Pressed. Current={current_pos}, New={new_position}")
            # else:
                # print(f"[GAMEPAD:BUTTON] Toggle {servo_id}: No change (State: {button_state}, Prev: {prev_state})")

        elif mode == "momentary":
            # Position directly follows button state
            target_position = max_pulse if button_state == 1 else min_pulse
            # Only return a position if it's different from current (optional optimization)
            # Requires reliable current position tracking for optimization to work
            # current_pos = getattr(getattr(servo, 'settings', None), 'position', None)
            # if current_pos is None or target_position != current_pos:
            #    new_position = target_position
            new_position = target_position # Simpler: always return target position
            # print(f"[GAMEPAD:BUTTON] Momentary {servo_id}: State={button_state}, Target={new_position}")

        else:
            print(f"[GAMEPAD:BUTTON] Unknown button mode '{mode}' for servo {servo_id}")

        # Update state history *after* processing logic based on prev_state
        button_states[state_key] = button_state

        return new_position

    except AttributeError as e:
        print(f"[GAMEPAD:BUTTON] Error accessing servo attributes for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None
    except Exception as e:
        print(f"[GAMEPAD:BUTTON] Error handling button control for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None


def handle_axis_control(servo, value: float, mode: Optional[str], multiplier: float, context: Dict[str, Any], original_control_type: Optional[str]) -> Optional[int]:
    """
    Handle axis-type controls (absolute or relative). Differentiates input range.
    """
    try:
        # Get servo physical limits
        min_pulse = servo.settings.min_pulse
        max_pulse = servo.settings.max_pulse
        servo_range = float(max_pulse - min_pulse)

        if servo_range <= 0:
             print(f"[GAMEPAD:AXIS] Invalid servo range for {servo.id}: min={min_pulse}, max={max_pulse}. Cannot proceed.")
             return None

        # Axis states (optional, mainly for relative mode if complex logic needed)
        # axis_states = context.setdefault("gamepad_axis_states", {})
        # servo_id = servo.id
        # state_key = f"{servo_id}"
        # prev_value = axis_states.get(state_key, 0.0)
        # axis_states[state_key] = value # Store current value

        # --- Apply Mode Logic ---
        new_position = None # Initialize to None

        if mode == "absolute":
            normalized_value = 0.0 # Value mapped to 0.0 - 1.0 range

            # *** Differentiate based on original control type ***
            if original_control_type == "axis":
                # Assume BIPOLAR input (-1.0 to 1.0) typical for joysticks
                clamped_value = max(-1.0, min(value, 1.0)) # Clamp input first
                normalized_value = (clamped_value + 1.0) / 2.0 # Map [-1, 1] to [0, 1]
                # print(f"[GAMEPAD:AXIS] Absolute (Bipolar): Servo {servo.id}, Val={value:.2f} -> Clamp={clamped_value:.2f} -> Norm={normalized_value:.2f}")
            else: # Assume "button" (acting as analog) or unknown -> UNIPOLAR (0.0 to 1.0)
                clamped_value = max(0.0, min(value, 1.0)) # Clamp input first
                normalized_value = clamped_value # Value is already in [0, 1] range
                # print(f"[GAMEPAD:AXIS] Absolute (Unipolar): Servo {servo.id}, Val={value:.2f} -> Clamp={clamped_value:.2f} -> Norm={normalized_value:.2f}")

            # Apply multiplier to adjust the *sensitivity* or *effective range* within the 0-1 space.
            center_point = 0.5
            effective_value = center_point + (normalized_value - center_point) * multiplier
            final_scaled_value = max(0.0, min(effective_value, 1.0))

            # Map the final [0.0, 1.0] value to the servo's pulse range
            new_position = int(min_pulse + (final_scaled_value * servo_range))
            # print(f"[GAMEPAD:AXIS] Absolute: Servo {servo.id} -> Norm={normalized_value:.2f} * Mult={multiplier:.2f} -> Scaled={final_scaled_value:.2f} -> Pos={new_position} (Range: {min_pulse}-{max_pulse})")


        elif mode == "relative":
            # Deadzone threshold to prevent drift from noisy axes near center
            deadzone = 0.1 # Adjust as needed
            if abs(value) > deadzone:
                # Clamp value to [-1.0, 1.0] to represent max speed/rate
                relative_rate = max(-1.0, min(value, 1.0))

                # Define a step size for relative movement per event
                # Make step proportional to servo range and multiplier for sensitivity control
                base_step_per_event = servo_range * 0.02 # Adjust base step % as needed
                change = relative_rate * multiplier * base_step_per_event

                # Get current position reliably
                current_pos = float(servo.settings.position)
                target_pos = current_pos + change

                # Clamp the target position to the servo's physical limits
                new_position = int(max(min_pulse, min(target_pos, max_pulse)))
                # print(f"[GAMEPAD:AXIS] Relative: Servo {servo.id}, Val={value:.2f} -> Rate={relative_rate:.2f}, Change={change:.2f}, Cur={current_pos}, New={new_position}")

            # If value is within the deadzone, new_position remains None (its initial value)
            # No 'else' block or 'pass' is needed here.

        else:
            print(f"[GAMEPAD:AXIS] Unknown axis mode '{mode}' for servo {servo.id}")

        return new_position # Will be None if within deadzone in relative mode, or calculated value otherwise

    except AttributeError as e:
        print(f"[GAMEPAD:AXIS] Error accessing servo attributes for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None
    except Exception as e:
        print(f"[GAMEPAD:AXIS] Error handling axis control for {getattr(servo, 'id', 'UNKNOWN')}: {e}")
        return None