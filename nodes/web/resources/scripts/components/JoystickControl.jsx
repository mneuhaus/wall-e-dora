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
  
  // Find the servo data from available servos
  useEffect(() => {
    if (availableServos && availableServos.length > 0) {
      // Update X servo info
      if (xServoId) {
        const targetXId = parseInt(xServoId);
        const xServo = availableServos.find(s => {
          const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
          return currentId === targetXId;
        });
        
        if (xServo) {
          setXServoInfo(xServo);
          setXPosition(xServo.position || 90);
        }
      }
      
      // Update Y servo info
      if (yServoId) {
        const targetYId = parseInt(yServoId);
        const yServo = availableServos.find(s => {
          const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
          return currentId === targetYId;
        });
        
        if (yServo) {
          setYServoInfo(yServo);
          setYPosition(yServo.position || 90);
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
    // Map to servo range (typically 0-180)
    
    let newXPosition, newYPosition;
    
    if (xServoId) {
      // Map -100 to 100 → 0 to 180 for X
      // (value + 100) * 180 / 200
      const xMin = xServoInfo?.min_pos !== undefined ? xServoInfo.min_pos : 0;
      const xMax = xServoInfo?.max_pos !== undefined ? xServoInfo.max_pos : 180;
      const xRange = xMax - xMin;
      
      // Calculate new position and round to integer
      newXPosition = Math.round(xMin + ((x + 100) / 200) * xRange);
      
      // Only update if position changed significantly (more than 1 degree)
      if (Math.abs(newXPosition - prevX.current) > 1) {
        setXPosition(newXPosition);
        prevX.current = newXPosition;
        node.emit('set_servo', [parseInt(xServoId), newXPosition, parseInt(speed)]);
      }
    }
    
    if (yServoId) {
      // Map -100 to 100 → 0 to 180 for Y (inverted as up is negative in joystick)
      // (100 - value) * 180 / 200
      const yMin = yServoInfo?.min_pos !== undefined ? yServoInfo.min_pos : 0;
      const yMax = yServoInfo?.max_pos !== undefined ? yServoInfo.max_pos : 180;
      const yRange = yMax - yMin;
      
      // Calculate new position and round to integer (invert y-axis)
      newYPosition = Math.round(yMin + ((100 - y) / 200) * yRange);
      
      // Only update if position changed significantly (more than 1 degree)
      if (Math.abs(newYPosition - prevY.current) > 1) {
        setYPosition(newYPosition);
        prevY.current = newYPosition;
        node.emit('set_servo', [parseInt(yServoId), newYPosition, parseInt(speed)]);
      }
    }
  };
  
  // Reset joystick to center
  const handleStop = () => {
    // Optional: Return to center position when joystick is released
    // This depends on the desired behavior
  };
  
  // Handle servo selection and save changes to widget props
  const handleXServoChange = (servoId) => {
    setXServoId(servoId);
    if (i) {
      updateWidgetProps(i, { xServoId: servoId });
    }
  };

  const handleYServoChange = (servoId) => {
    setYServoId(servoId);
    if (i) {
      updateWidgetProps(i, { yServoId: servoId });
    }
  };

  const handleSpeedChange = (newSpeed) => {
    const speedValue = parseInt(newSpeed);
    setSpeed(speedValue);
    if (i) {
      updateWidgetProps(i, { speed: speedValue });
    }
  };

  // Settings panel content
  const SettingsPanel = () => (
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
  );

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