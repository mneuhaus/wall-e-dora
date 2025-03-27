"""
Gamepad event handler for the Waveshare Servo Node.

Handles gamepad button and axis events and maps them to servo movements
based on the servo settings' gamepad configuration.
"""

from typing import Dict, Any, Optional

def handle_gamepad_event(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Handle gamepad button and axis events and map them to servo movements.
    
    Args:
        event: The event data containing control name and value
        context: The node context containing servos and other state
    """
    control_name = event.get("id")
    raw_value = event.get("value")
    
    # The safest and simplest extraction method that won't fail
    try:
        # Handle PyArrow arrays (most common case)
        if hasattr(raw_value, "__getitem__") and len(raw_value) > 0:
            # If it has as_py method, use it
            if hasattr(raw_value[0], "as_py"):
                value = raw_value[0].as_py()
            # Otherwise try string conversion as fallback
            else:
                raw_str = str(raw_value[0]).strip('"\'')
                try:
                    value = float(raw_str)
                except (ValueError, TypeError):
                    print(f"[GAMEPAD] Warning: Could not convert '{raw_str}' to number")
                    value = 0
        # Handle simple values
        elif isinstance(raw_value, (int, float)):
            value = float(raw_value)
        # Handle string values
        elif isinstance(raw_value, str):
            try:
                value = float(raw_value)
            except (ValueError, TypeError):
                print(f"[GAMEPAD] Warning: Could not convert string '{raw_value}' to number")
                value = 0
        # Fallback for any other type
        else:
            print(f"[GAMEPAD] Warning: Unsupported value type: {type(raw_value)}")
            value = 0
    except Exception as e:
        print(f"[GAMEPAD] Error extracting value: {e}")
        value = 0  # Default to 0 so we don't break later comparisons
    
    # Convert value to float and normalize negative values
    try:
        if isinstance(value, str):
            value = float(value)
        if value < 0:
            value = abs(value)
    except (ValueError, TypeError):
        # If conversion fails, use 0 as default
        value = 0
    
    if control_name is None:
        print(f"[GAMEPAD] Invalid gamepad event (no control name): {event}")
        return
    
    # Find servos mapped to this control
    mapped_servos = find_servos_by_control(control_name, context)
    
    if not mapped_servos:
        # print(f"[GAMEPAD] No servos mapped to control '{control_name}'")
        return
    
    print(f"[GAMEPAD] Found {len(mapped_servos)} servo(s) mapped to '{control_name}'")
    
    # Process each mapped servo
    for servo in mapped_servos:
        servo_id = servo.id
        config = servo.settings.gamepad_config
        control_type = config.get("type") if config else "unknown"
        control_mode = config.get("mode") if config else "unknown"
        
        print(f"[GAMEPAD] Processing servo {servo_id} with {control_type}/{control_mode} mapping")
        
        # Calculate servo position based on mapping configuration
        position = calculate_position(servo, value, context)
        
        if position is not None:
            print(f"[GAMEPAD] Moving servo {servo_id} to position {position}")
            # Move the servo
            from waveshare_servo.inputs.move_servo import move_servo
            # Call the move_servo function directly with the correct parameters
            move_servo(context, servo_id, position)
        else:
            print(f"[GAMEPAD] No position change for servo {servo_id}")


def find_servos_by_control(control_name: str, context: Dict[str, Any]) -> list:
    """
    Find all servos mapped to a specific gamepad control.
    
    Args:
        control_name: The gamepad control name (e.g., "FACE_1", "LEFT_ANALOG_STICK_X")
        context: The node context containing servos and other state
        
    Returns:
        A list of servo objects mapped to the control
    """
    servos = context.get("servos", {})
    print(f"[GAMEPAD:FIND] Looking for servos mapped to control '{control_name}'")
    
    # For debugging, print all servo mappings
    for servo_id, servo in servos.items():
        attached = servo.settings.attached_control
        if attached:
            print(f"[GAMEPAD:FIND] Servo {servo_id} is mapped to '{attached}'")
    
    # Find matching servos
    matched_servos = [servo for servo in servos.values() 
                      if servo.settings.attached_control == control_name]
    
    if matched_servos:
        servo_ids = [s.id for s in matched_servos]
        print(f"[GAMEPAD:FIND] Found {len(matched_servos)} servos: {servo_ids}")
    else:
        print(f"[GAMEPAD:FIND] No servos found for control '{control_name}'")
        
    return matched_servos


def calculate_position(servo, value, context: Dict[str, Any]) -> Optional[int]:
    """
    Calculate servo position based on control value and mapping configuration.
    
    Args:
        servo: The servo object
        value: The gamepad control value (0/1 for buttons, -1.0 to 1.0 for axes)
        context: The node context
        
    Returns:
        The calculated position (0-1023) or None if no position change
    """
    config = servo.settings.gamepad_config
    if not config:
        return None
        
    control_type = config.get("type")
    control_mode = config.get("mode")
    invert = config.get("invert", False)
    multiplier = config.get("multiplier", 1.0)
    
    # Apply inversion if needed
    if invert:
        if control_type == "axis":
            value = -value
        elif control_type == "button":
            value = 1 - value
    
    # Handle different control types and modes
    if control_type == "button":
        # If the button is in an analog mode, use the axis handler
        if control_mode in ["absolute", "relative"]:
            return handle_axis_control(servo, value, control_mode, multiplier, context)
        else:
            return handle_button_control(servo, value, control_mode, context)
    elif control_type == "axis":
        return handle_axis_control(servo, value, control_mode, multiplier, context)
    
    return None


def handle_button_control(servo, value, mode, context: Dict[str, Any]) -> Optional[int]:
    """
    Handle button-type controls (toggle or momentary).
    
    Args:
        servo: The servo object
        value: The button value (0 or 1)
        mode: The control mode ("toggle" or "momentary")
        context: The node context
        
    Returns:
        The calculated position (0-1023) or None if no position change
    """
    # Ensure value is numeric and convert to 0/1
    try:
        # Convert to float if needed
        if isinstance(value, str):
            try:
                value = float(value)
            except (ValueError, TypeError):
                print(f"[GAMEPAD:BUTTON] Invalid button value (non-numeric string): {value}")
                return None
                
        # Now value should be numeric, check if it's pressed
        if isinstance(value, (int, float)):
            is_pressed = float(value) > 0.5
            button_value = 1 if is_pressed else 0
        else:
            print(f"[GAMEPAD:BUTTON] Invalid button value (unknown type): {value}")
            return None
    except Exception as e:
        print(f"[GAMEPAD:BUTTON] Error processing button value: {e}")
        return None
        
    # Get button state tracking dict
    button_states = context.setdefault("gamepad_button_states", {})
    servo_id = servo.id
    
    # Get previous state or set default
    state_key = f"{servo_id}"
    prev_state = button_states.get(state_key, 0)
    if isinstance(prev_state, str):
        try:
            prev_state = float(prev_state)
        except (ValueError, TypeError):
            prev_state = 0
    
    if mode == "toggle":
        # Toggle mode: Change position only on button press (0->1)
        if button_value == 1 and prev_state == 0:
            # Toggle between min and max position from the servo settings
            current_pos = servo.settings.position
            min_pulse = servo.settings.min_pulse
            max_pulse = servo.settings.max_pulse
            middle_point = min_pulse + (max_pulse - min_pulse) / 2
            
            # Toggle between min_pulse and max_pulse
            if current_pos > middle_point:  # If in upper half of range
                new_position = min_pulse  # Go to min_pulse
            else:
                new_position = max_pulse  # Go to max_pulse
            
            # Update state
            button_states[state_key] = button_value
            return new_position
    
    elif mode == "momentary":
        # Momentary mode: Position follows button state
        min_pulse = servo.settings.min_pulse
        max_pulse = servo.settings.max_pulse
        new_position = max_pulse if button_value == 1 else min_pulse
        button_states[state_key] = button_value
        return new_position
    
    # Update state even if we didn't change position
    button_states[state_key] = button_value
    return None


def handle_axis_control(servo, value, mode, multiplier, context: Dict[str, Any]) -> Optional[int]:
    """
    Handle axis-type controls (absolute or relative).
    
    Args:
        servo: The servo object
        value: The axis value (-1.0 to 1.0)
        mode: The control mode ("absolute" or "relative")
        multiplier: The sensitivity multiplier
        context: The node context
        
    Returns:
        The calculated position (0-1023) or None if no position change
    """
    # Ensure value is treated as a float
    try:
        # Convert to float if needed
        if isinstance(value, str):
            try:
                value = float(value)
            except (ValueError, TypeError):
                print(f"[GAMEPAD:AXIS] Invalid axis value (non-numeric string): {value}")
                return None
                
        # Now value should be numeric
        if isinstance(value, (int, float)):
            float_value = float(value)
        else:
            print(f"[GAMEPAD:AXIS] Invalid axis value (unknown type): {value}")
            return None
    except (ValueError, TypeError):
        print(f"[GAMEPAD:AXIS] Cannot convert to number: {value}")
        return None
    except Exception as e:
        print(f"[GAMEPAD:AXIS] Error processing axis value: {e}")
        return None
    
    # Get axis state tracking dict
    axis_states = context.setdefault("gamepad_axis_states", {})
    servo_id = servo.id
    
    # Store current state
    prev_value = axis_states.get(f"{servo_id}", 0)
    if isinstance(prev_value, str):
        try:
            prev_value = float(prev_value)
        except (ValueError, TypeError):
            prev_value = 0
    
    axis_states[f"{servo_id}"] = float_value
    
    if mode == "absolute":
        # Absolute mode: Map 0.0 to 1.0 to servo range 0-1023
        # Apply multiplier to adjust sensitivity
        scaled_value = float_value * multiplier
        # Clamp to 0.0 to 1.0 range
        scaled_value = max(min(scaled_value, 1.0), 0.0)
        # Map to servo range
        new_position = int(scaled_value * 1023)
        return new_position
    
    elif mode == "relative":
        # Relative mode: Change position based on axis movement
        # Only apply change if value is significantly different from zero
        if abs(float_value) > 0.1:
            # Calculate change amount (apply multiplier for sensitivity)
            change = float_value * multiplier * 10  # Adjust for reasonable speed
            # Update position
            current_pos = servo.settings.position
            new_pos = current_pos + change
            # Clamp to valid range
            new_position = int(max(min(new_pos, 1023), 0))
            return new_position
    
    return None