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
    
    print(f"[GAMEPAD:DEBUG] Raw value type: {type(raw_value)}, value: {raw_value}")
    
    # Handle PyArrow Int64Array specifically
    if str(type(raw_value)).find('pyarrow.lib.Int64Array') >= 0:
        try:
            # Extract the value directly from the array
            import pyarrow as pa
            value = raw_value[0].as_py() if len(raw_value) > 0 else 0
            print(f"[GAMEPAD] Extracted value {value} from PyArrow Int64Array")
        except Exception as e:
            print(f"[GAMEPAD] Error extracting from PyArrow Int64Array: {e}")
            try:
                # Alternative extraction method
                value = int(str(raw_value).split('[')[1].split(']')[0].strip())
                print(f"[GAMEPAD] Extracted value {value} using string parsing")
            except Exception as e2:
                print(f"[GAMEPAD] Error with string parsing: {e2}")
                value = 0
    # Handle Apache Arrow arrays by converting to Python values
    elif hasattr(raw_value, "as_py"):
        try:
            # This is an Arrow scalar
            value = raw_value.as_py()
            print(f"[GAMEPAD] Converted Arrow scalar to Python value: {value}")
        except Exception as e:
            print(f"[GAMEPAD] Error converting Arrow scalar: {e}")
            value = 0
    elif isinstance(raw_value, list) and len(raw_value) > 0:
        # This might be an Arrow array
        if hasattr(raw_value[0], "as_py"):
            try:
                value = raw_value[0].as_py()
                print(f"[GAMEPAD] Converted Arrow array element to Python value: {value}")
            except Exception as e:
                print(f"[GAMEPAD] Error converting Arrow array element: {e}")
                value = 0
        else:
            # Regular Python list
            value = raw_value[0]
            print(f"[GAMEPAD] Using first element of Python list: {value}")
    elif isinstance(raw_value, str) and raw_value.strip().startswith("["):
        # This handles the case where the value might be formatted as a string representation of an array
        try:
            # Try to find a digit in the string
            import re
            digit_match = re.search(r'-?\d+(\.\d+)?', raw_value)
            if digit_match:
                value = float(digit_match.group())
                print(f"[GAMEPAD] Extracted value {value} from string array: {raw_value}")
            else:
                print(f"[GAMEPAD] No number found in string array: {raw_value}")
                value = 0
        except Exception as e:
            print(f"[GAMEPAD] Error extracting value from string array: {e}")
            value = 0
    else:
        value = raw_value
        print(f"[GAMEPAD] Using value as is: {value}")
    
    if control_name is None or value is None:
        print(f"[GAMEPAD] Invalid gamepad event: {event}")
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
    # Handle PyArrow Int64Array
    if str(type(value)).find('pyarrow.lib.Int64Array') >= 0:
        try:
            # Extract the value directly from the array
            value_int = value[0].as_py() if len(value) > 0 else 0
            print(f"[GAMEPAD:BUTTON] Extracted button value {value_int} from PyArrow Int64Array")
            value = value_int
        except Exception as e:
            print(f"[GAMEPAD:BUTTON] Error extracting from PyArrow Int64Array: {e}")
            try:
                # Alternative extraction method
                value = int(str(value).split('[')[1].split(']')[0].strip())
                print(f"[GAMEPAD:BUTTON] Extracted button value {value} using string parsing")
            except Exception as e2:
                print(f"[GAMEPAD:BUTTON] Error with string parsing: {e2}")
                return None
    # Handle other Apache Arrow values
    elif hasattr(value, "as_py"):
        try:
            value = value.as_py()
            print(f"[GAMEPAD:BUTTON] Converted Arrow value to {value}")
        except Exception as e:
            print(f"[GAMEPAD:BUTTON] Error converting Arrow value: {e}")
            return None
    
    # Handle list values including Arrow arrays
    elif isinstance(value, list) and len(value) > 0:
        if hasattr(value[0], "as_py"):
            try:
                value = value[0].as_py()
                print(f"[GAMEPAD:BUTTON] Converted Arrow array element to {value}")
            except Exception as e:
                print(f"[GAMEPAD:BUTTON] Error converting Arrow array element: {e}")
                return None
        else:
            value = value[0]
            print(f"[GAMEPAD:BUTTON] Using first value from list: {value}")
    elif isinstance(value, str) and value.strip().startswith("["):
        # This handles the case where the value might be formatted as a string representation of an array
        try:
            # Try to find a digit in the string
            import re
            digit_match = re.search(r'\d+', value)
            if digit_match:
                value = int(digit_match.group())
                print(f"[GAMEPAD:BUTTON] Extracted value {value} from string")
            else:
                print(f"[GAMEPAD:BUTTON] No digit found in string value: {value}")
                return None
        except Exception as e:
            print(f"[GAMEPAD:BUTTON] Error extracting value from string array: {e}")
            return None
    
    # Ensure value is treated as a number
    try:
        value = int(float(value))
        print(f"[GAMEPAD:BUTTON] Final button value: {value}")
    except (ValueError, TypeError):
        print(f"[GAMEPAD:BUTTON] Cannot convert to number: {value}")
        return None
    
    # Get button state tracking dict
    button_states = context.setdefault("gamepad_button_states", {})
    servo_id = servo.id
    
    # Debug the button_states dict
    print(f"[GAMEPAD:BUTTON:DEBUG] All button states: {button_states}")
    
    # Get previous state or set default
    state_key = f"{servo_id}"
    prev_state = button_states.get(state_key, 0)
    print(f"[GAMEPAD:BUTTON] Servo {servo_id}, mode={mode}, value={value}, prev_state={prev_state}, state_key={state_key}")
    
    if mode == "toggle":
        # Toggle mode: Change position only on button press (0->1)
        print(f"[GAMEPAD:BUTTON] TOGGLE MODE DEBUG: value={value}, prev_state={prev_state}, values equal: {value == prev_state}")
        if int(value) == 1 and int(prev_state) == 0:
            # Toggle between min and max position from the servo settings
            current_pos = servo.settings.position
            min_pulse = servo.settings.min_pulse
            max_pulse = servo.settings.max_pulse
            middle_point = min_pulse + (max_pulse - min_pulse) / 2
            
            print(f"[GAMEPAD:BUTTON] Toggle mode, current position: {current_pos}, min: {min_pulse}, max: {max_pulse}, mid: {middle_point}")
            
            # Toggle between min_pulse and max_pulse
            if current_pos > middle_point:  # If in upper half of range
                new_position = min_pulse  # Go to min_pulse
                print(f"[GAMEPAD:BUTTON] Toggling to MIN position ({min_pulse})")
            else:
                new_position = max_pulse  # Go to max_pulse
                print(f"[GAMEPAD:BUTTON] Toggling to MAX position ({max_pulse})")
            
            # Update state
            button_states[f"{servo_id}"] = value
            return new_position
    
    elif mode == "momentary":
        # Momentary mode: Position follows button state
        min_pulse = servo.settings.min_pulse
        max_pulse = servo.settings.max_pulse
        new_position = max_pulse if value == 1 else min_pulse
        print(f"[GAMEPAD:BUTTON] Momentary mode, setting to {new_position} (using min: {min_pulse}, max: {max_pulse})")
        button_states[f"{servo_id}"] = value
        return new_position
    
    # Update state even if we didn't change position
    button_states[f"{servo_id}"] = value
    print(f"[GAMEPAD:BUTTON] No position change")
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
    # Handle PyArrow Int64Array or Float64Array
    if str(type(value)).find('pyarrow.lib') >= 0:
        try:
            # Extract the value directly from the array
            value_float = float(value[0].as_py()) if len(value) > 0 else 0.0
            print(f"[GAMEPAD:AXIS] Extracted axis value {value_float} from PyArrow array")
            value = value_float
        except Exception as e:
            print(f"[GAMEPAD:AXIS] Error extracting from PyArrow array: {e}")
            try:
                # Alternative extraction method
                value = float(str(value).split('[')[1].split(']')[0].strip())
                print(f"[GAMEPAD:AXIS] Extracted axis value {value} using string parsing")
            except Exception as e2:
                print(f"[GAMEPAD:AXIS] Error with string parsing: {e2}")
                return None
    # Handle other Apache Arrow values
    elif hasattr(value, "as_py"):
        try:
            value = value.as_py()
            print(f"[GAMEPAD:AXIS] Converted Arrow value to {value}")
        except Exception as e:
            print(f"[GAMEPAD:AXIS] Error converting Arrow value: {e}")
            return None
    
    # Handle list values including Arrow arrays
    elif isinstance(value, list) and len(value) > 0:
        if hasattr(value[0], "as_py"):
            try:
                value = value[0].as_py()
                print(f"[GAMEPAD:AXIS] Converted Arrow array element to {value}")
            except Exception as e:
                print(f"[GAMEPAD:AXIS] Error converting Arrow array element: {e}")
                return None
        else:
            value = value[0]
            print(f"[GAMEPAD:AXIS] Using first value from list: {value}")
    elif isinstance(value, str) and value.strip().startswith("["):
        # This handles the case where the value might be formatted as a string representation of an array
        try:
            # Try to find a float in the string
            import re
            float_match = re.search(r'-?\d+(\.\d+)?', value)
            if float_match:
                value = float(float_match.group())
                print(f"[GAMEPAD:AXIS] Extracted value {value} from string array")
            else:
                print(f"[GAMEPAD:AXIS] No number found in string value: {value}")
                return None
        except Exception as e:
            print(f"[GAMEPAD:AXIS] Error extracting value from string array: {e}")
            return None
    
    # Ensure value is treated as a float
    try:
        value = float(value)
        print(f"[GAMEPAD:AXIS] Final axis value: {value:.2f}")
    except (ValueError, TypeError):
        print(f"[GAMEPAD:AXIS] Cannot convert to number: {value}")
        return None
    
    # Get axis state tracking dict
    axis_states = context.setdefault("gamepad_axis_states", {})
    servo_id = servo.id
    
    # Store current state
    prev_value = axis_states.get(f"{servo_id}", 0)
    axis_states[f"{servo_id}"] = value
    
    print(f"[GAMEPAD:AXIS] Servo {servo_id}, mode={mode}, value={value:.2f}, multiplier={multiplier}")
    
    if mode == "absolute":
        # Absolute mode: Map -1.0 to 1.0 to servo range 0-1023
        # Apply multiplier to adjust sensitivity (lower value = less sensitive)
        scaled_value = value * multiplier
        # Clamp to -1.0 to 1.0 range
        scaled_value = max(min(scaled_value, 1.0), -1.0)
        # Map to servo range
        new_position = int(((scaled_value + 1.0) / 2.0) * 1023)
        print(f"[GAMEPAD:AXIS] Absolute mode: value={value:.2f} → scaled={scaled_value:.2f} → position={new_position}")
        return new_position
    
    elif mode == "relative":
        # Relative mode: Change position based on axis movement
        # Only apply change if value is significantly different from zero
        if abs(value) > 0.1:
            # Calculate change amount (apply multiplier for sensitivity)
            change = value * multiplier * 10  # Adjust for reasonable speed
            # Update position
            current_pos = servo.settings.position
            new_pos = current_pos + change
            # Clamp to valid range
            new_position = int(max(min(new_pos, 1023), 0))
            print(f"[GAMEPAD:AXIS] Relative mode: current={current_pos} → change={change:.2f} → new={new_position}")
            return new_position
        else:
            print(f"[GAMEPAD:AXIS] Value too small ({value:.2f}), ignoring")
    
    print(f"[GAMEPAD:AXIS] No position change")
    return None