"""
Wiggle operation for servo identification.
"""

import time


def wiggle_servo(servo, wiggle_range=300, iterations=3):
    """
    Wiggle a servo for identification by moving it back and forth.
    
    Args:
        servo: The servo object to wiggle
        wiggle_range: The number of pulse units to move in each direction
        iterations: Number of times to complete the wiggle pattern
        
    Returns:
        bool: True if wiggle was successful, False otherwise
    """
    try:
        print(f"Wiggling servo {servo.id}")
        
        # Get current position - use a small offset if position is None/0
        current_pos = servo.settings.position
        if current_pos is None or current_pos == 0:
            # Use the middle of min/max range as fallback
            current_pos = (servo.settings.min_pulse + servo.settings.max_pulse) // 2
            print(f"No current position, using midpoint: {current_pos}")
        
        # Store original speed for restoration later
        original_speed = servo.settings.speed
        # Set a very fast speed for wiggling - 50 is the minimum (fastest)
        servo.settings.speed = 50  # Make wiggle very fast for better visibility
        
        # Calculate wiggle size based on the servo's range
        servo_range = servo.settings.max_pulse - servo.settings.min_pulse
        # Adjust wiggle range to be proportional to the servo's range but at least 200 units
        wiggle_range = max(200, min(wiggle_range, int(servo_range * 0.15)))  # 15% of servo range or at least 200
        
        print(f"Wiggling servo {servo.id} at position {current_pos} with range ±{wiggle_range}")
        
        # Send direct commands for faster response
        try:
            # Send setup command to ensure the servo is initialized
            servo.send_command(f"P{current_pos}T{servo.settings.speed}")
            time.sleep(0.3)  # Wait for it to reach start position
            
            # Perform wiggle pattern with direct commands
            for i in range(iterations):
                # Abrupt movements for better visibility
                servo.send_command(f"P{current_pos - wiggle_range}T50")  # Left fast
                time.sleep(0.1)
                servo.send_command(f"P{current_pos + wiggle_range}T50")  # Right fast  
                time.sleep(0.1)
                servo.send_command(f"P{current_pos - wiggle_range}T50")  # Left fast
                time.sleep(0.1)
                servo.send_command(f"P{current_pos + wiggle_range}T50")  # Right fast
                time.sleep(0.1)
                
                # Small pause between iterations
                if i < iterations - 1:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error during direct wiggle commands: {e}")
            # Fallback to standard move method if direct commands fail
            for i in range(iterations):
                print(f"Fallback wiggle iteration {i+1}/{iterations}")
                
                # More pronounced movements - left, right, left, right, center
                positions = [
                    current_pos - wiggle_range,  # Far left
                    current_pos + wiggle_range,  # Far right
                    current_pos - wiggle_range,  # Far left
                    current_pos + wiggle_range,  # Far right
                    current_pos,                 # Back to center
                ]
                
                for pos in positions:
                    # Ensure position stays within servo min/max range
                    safe_pos = max(
                        servo.settings.min_pulse, min(servo.settings.max_pulse, pos)
                    )
                    servo.move(safe_pos)
                    time.sleep(0.1)  # Very short delay for fast wiggle
        
        # Return to center position at normal speed
        servo.settings.speed = original_speed
        servo.move(current_pos)
        
        print(f"Wiggle complete for servo {servo.id}")
        return True
    except Exception as e:
        print(f"Error wiggling servo {servo.id}: {e}")
        
        # Try to restore speed even if there was an error
        try:
            servo.settings.speed = original_speed
        except:
            pass
            
        return False