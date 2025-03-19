import React, { useState, useEffect, useRef } from 'react';
import Joystick from 'rc-joystick';
import node from '../Node';
import { useAppContext } from '../contexts/AppContext';
import { useGridContext } from '../contexts/GridContext';
import ServoSelector from './ServoSelector';

const JoystickControl = ({ 
  xServoId: initialXServoId, 
  yServoId: initialYServoId,
  inSettingsModal = false,
  showSettings = false,
  i, // Widget ID
  ...widgetProps // Remaining widget properties
}) => {
  const { availableServos } = useAppContext();
  const { isEditable, updateWidgetProps } = useGridContext();
  const [xServoId, setXServoId] = useState(initialXServoId);
  const [yServoId, setYServoId] = useState(initialYServoId);
  const [xPosition, setXPosition] = useState(90); // Default to center (90 degrees)
  const [yPosition, setYPosition] = useState(90); // Default to center (90 degrees)
  const [speed, setSpeed] = useState(100);
  const [xServoInfo, setXServoInfo] = useState(null);
  const [yServoInfo, setYServoInfo] = useState(null);
  const prevX = useRef(90);
  const prevY = useRef(90);
  
  // Initialize from widget props when component mounts
  useEffect(() => {
    console.log("JoystickControl initializing with props:", { initialXServoId, initialYServoId, i: i });
    
    // Set initial values from props
    if (initialXServoId !== undefined) {
      const parsedXId = initialXServoId === null ? null : parseInt(initialXServoId);
      console.log(`Setting initial X servo ID: ${parsedXId} for widget ${i}`);
      setXServoId(parsedXId);
    }
    
    if (initialYServoId !== undefined) {
      const parsedYId = initialYServoId === null ? null : parseInt(initialYServoId);
      console.log(`Setting initial Y servo ID: ${parsedYId} for widget ${i}`);
      setYServoId(parsedYId);
    }
    
    // If we're missing initial values but have widget ID, ensure they're explicitly set to null
    // This helps with debugging and ensures initialState is properly tracked
    if (i && (initialXServoId === undefined || initialYServoId === undefined)) {
      console.log(`Widget ${i} missing servo assignments, ensuring props are initialized`);
      
      // Update widget props if needed
      if (initialXServoId === undefined) {
        updateWidgetProps(i, { xServoId: null });
      }
      
      if (initialYServoId === undefined) {
        updateWidgetProps(i, { yServoId: null });
      }
    }
  }, [i, initialXServoId, initialYServoId]);  // Run when these props change
  
  // Find the servo data from available servos
  useEffect(() => {
    if (availableServos && availableServos.length > 0) {
      console.log("Updating servo info with available servos", { 
        availableServos: availableServos.map(s => s.id),
        xServoId,
        yServoId
      });
      
      // Update X servo info
      if (xServoId) {
        const targetXId = parseInt(xServoId);
        console.log("Looking for X servo with ID:", targetXId);
        const xServo = availableServos.find(s => {
          const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
          return currentId === targetXId;
        });
        
        if (xServo) {
          console.log("Found X servo:", xServo);
          setXServoInfo(xServo);
          setXPosition(xServo.position || 90);
        } else {
          console.log("X servo not found in available servos");
        }
      }
      
      // Update Y servo info
      if (yServoId) {
        const targetYId = parseInt(yServoId);
        console.log("Looking for Y servo with ID:", targetYId);
        const yServo = availableServos.find(s => {
          const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
          return currentId === targetYId;
        });
        
        if (yServo) {
          console.log("Found Y servo:", yServo);
          setYServoInfo(yServo);
          setYPosition(yServo.position || 90);
        } else {
          console.log("Y servo not found in available servos");
        }
      }
    }
  }, [availableServos, xServoId, yServoId]);
  
  // Listen for servo updates from WebSocket
  useEffect(() => {
    const unsubscribe = node.on('servo_status', (event) => {
      if (event && event.value) {
        const servos = event.value || [];
        
        // Update X servo
        if (xServoId) {
          const targetXId = parseInt(xServoId);
          const xServo = servos.find(s => {
            const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
            return currentId === targetXId;
          });
          
          if (xServo) {
            setXServoInfo(xServo);
            setXPosition(xServo.position || 90);
          }
        }
        
        // Update Y servo
        if (yServoId) {
          const targetYId = parseInt(yServoId);
          const yServo = servos.find(s => {
            const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
            return currentId === targetYId;
          });
          
          if (yServo) {
            setYServoInfo(yServo);
            setYPosition(yServo.position || 90);
          }
        }
      }
    });
    
    // Request servo data on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, [xServoId, yServoId]);
  
  // Handle joystick movement
  const handleMove = (evt) => {
    const { x, y } = evt;
    
    // Convert x, y to servo positions
    // x and y values come from joystick as -100 to 100
    // Map to servo range (using min_pos and max_pos from servo info)
    
    let newXPosition, newYPosition;
    
    if (xServoId && xServoInfo) {
      console.log(`X joystick at ${x} mapped to servo ${xServoId}`);
      
      // Get the min and max from servo info, with fallbacks
      const xMin = xServoInfo?.min_pos !== undefined ? xServoInfo.min_pos : 0;
      const xMax = xServoInfo?.max_pos !== undefined ? xServoInfo.max_pos : 1000;
      const xRange = xMax - xMin;
      
      // Calculate new position and round to integer
      // Map joystick (-100 to 100) to servo range
      newXPosition = Math.round(xMin + ((x + 100) / 200) * xRange);
      
      // Debug log for first few movements
      if (Math.abs(newXPosition - prevX.current) > 20) {
        console.log(`X movement: joystick=${x}, servo min=${xMin}, max=${xMax}, newPos=${newXPosition}`);
      }
      
      // Only update if position changed significantly (more than 1 position unit)
      if (Math.abs(newXPosition - prevX.current) > 1) {
        setXPosition(newXPosition);
        prevX.current = newXPosition;
        node.emit('set_servo', [parseInt(xServoId), newXPosition, parseInt(speed)]);
      }
    }
    
    if (yServoId && yServoInfo) {
      console.log(`Y joystick at ${y} mapped to servo ${yServoId}`);
      
      // Get the min and max from servo info, with fallbacks
      const yMin = yServoInfo?.min_pos !== undefined ? yServoInfo.min_pos : 0;
      const yMax = yServoInfo?.max_pos !== undefined ? yServoInfo.max_pos : 1000;
      const yRange = yMax - yMin;
      
      // Calculate new position and round to integer (invert y-axis)
      // Map joystick (-100 to 100) to servo range (inverted since up is negative)
      newYPosition = Math.round(yMin + ((100 - y) / 200) * yRange);
      
      // Debug log for first few movements
      if (Math.abs(newYPosition - prevY.current) > 20) {
        console.log(`Y movement: joystick=${y}, servo min=${yMin}, max=${yMax}, newPos=${newYPosition}`);
      }
      
      // Only update if position changed significantly (more than 1 position unit)
      if (Math.abs(newYPosition - prevY.current) > 1) {
        setYPosition(newYPosition);
        prevY.current = newYPosition;
        node.emit('set_servo', [parseInt(yServoId), newYPosition, parseInt(speed)]);
      }
    }
  };
  
  // Reset joystick to center when released
  const handleStop = () => {
    // Create center positions for both servos if they're assigned
    if (xServoId && xServoInfo) {
      const xMin = xServoInfo?.min_pos !== undefined ? xServoInfo.min_pos : 0;
      const xMax = xServoInfo?.max_pos !== undefined ? xServoInfo.max_pos : 1000;
      const xCenter = Math.round(xMin + (xMax - xMin) / 2);
      
      // Only center if it's sufficiently different from current position
      if (Math.abs(xCenter - prevX.current) > 10) {
        console.log(`Centering X servo ${xServoId} to position ${xCenter}`);
        setXPosition(xCenter);
        prevX.current = xCenter;
        node.emit('set_servo', [parseInt(xServoId), xCenter, parseInt(speed)]);
      }
    }
    
    if (yServoId && yServoInfo) {
      const yMin = yServoInfo?.min_pos !== undefined ? yServoInfo.min_pos : 0;
      const yMax = yServoInfo?.max_pos !== undefined ? yServoInfo.max_pos : 1000;
      const yCenter = Math.round(yMin + (yMax - yMin) / 2);
      
      // Only center if it's sufficiently different from current position
      if (Math.abs(yCenter - prevY.current) > 10) {
        console.log(`Centering Y servo ${yServoId} to position ${yCenter}`);
        setYPosition(yCenter);
        prevY.current = yCenter;
        node.emit('set_servo', [parseInt(yServoId), yCenter, parseInt(speed)]);
      }
    }
  };
  
  // Handle servo selection and save changes to widget props
  const handleXServoChange = (servoId) => {
    console.log("Setting X Servo:", servoId);
    // Update local state immediately
    setXServoId(servoId);
    
    // Save to widget props with higher priority
    if (i) {
      console.log(`Saving X Servo: ${servoId} to widget ${i}`);
      // Force update with higher priority and ensure it completes
      try {
        // Delay to ensure the selection is stable
        setTimeout(() => {
          // Use a simpler approach with direct property assignment
          node.emit('save_joystick_servo', {
            data: {
              id: i,
              axis: 'x',
              servoId: servoId === null ? null : parseInt(servoId)
            }
          });
          
          // Also update through the regular mechanism
          updateWidgetProps(i, { 
            xServoId: servoId === null ? null : parseInt(servoId) 
          });
          
          console.log(`X servo ${servoId} saved for widget ${i}`);
        }, 250);
      } catch (err) {
        console.error("Error saving X servo:", err);
      }
    }
  };

  const handleYServoChange = (servoId) => {
    console.log("Setting Y Servo:", servoId);
    // Update local state immediately
    setYServoId(servoId);
    
    // Save to widget props with higher priority
    if (i) {
      console.log(`Saving Y Servo: ${servoId} to widget ${i}`);
      // Force update with higher priority and ensure it completes
      try {
        // Delay to ensure the selection is stable
        setTimeout(() => {
          // Use a simpler approach with direct property assignment  
          node.emit('save_joystick_servo', {
            data: {
              id: i,
              axis: 'y',
              servoId: servoId === null ? null : parseInt(servoId)
            }
          });
          
          // Also update through the regular mechanism
          updateWidgetProps(i, { 
            yServoId: servoId === null ? null : parseInt(servoId) 
          });
          
          console.log(`Y servo ${servoId} saved for widget ${i}`);
        }, 250);
      } catch (err) {
        console.error("Error saving Y servo:", err);
      }
    }
  };

  const handleSpeedChange = (newSpeed) => {
    const speedValue = parseInt(newSpeed);
    setSpeed(speedValue);
    if (i) {
      updateWidgetProps(i, { speed: speedValue });
    }
  };

  // Settings panel content - memoized to prevent re-renders
  const SettingsPanel = React.memo(() => (
    <div className="joystick-settings">
      <ServoSelector 
        value={xServoId} 
        onChange={handleXServoChange} 
        label="X-Axis Servo"
      />
      <ServoSelector 
        value={yServoId} 
        onChange={handleYServoChange} 
        label="Y-Axis Servo"
      />
      <div className="speed-control">
        <label className="speed-label">Speed</label>
        <input 
          type="range" 
          min="1" 
          max="100" 
          value={speed} 
          onChange={(e) => handleSpeedChange(e.target.value)}
          className="speed-slider"
        />
        <div className="speed-value">{speed}%</div>
      </div>
    </div>
  ), [xServoId, yServoId, speed, handleXServoChange, handleYServoChange, handleSpeedChange]);
  
  // If only rendering in the settings modal
  if (inSettingsModal) {
    return <SettingsPanel />;
  }

  return (
    <div className="joystick-control-container">
      <div className="joystick-wrapper">
        <Joystick 
          size={150}
          sticky={false}
          baseColor="var(--surface-variant)"
          stickColor="var(--primary)"
          move={handleMove}
          stop={handleStop}
        />
      </div>
      
      <div className="joystick-status">
        {xServoId && <div className="joystick-position">X: {xPosition}°</div>}
        {yServoId && <div className="joystick-position">Y: {yPosition}°</div>}
      </div>
    </div>
  );
};

export default JoystickControl;