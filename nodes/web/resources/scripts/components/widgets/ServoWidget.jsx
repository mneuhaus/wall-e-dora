import React, { useState, useEffect } from 'react';
import node from '../../Node';
import { useAppContext } from '../../contexts/AppContext';
import { useGridContext } from '../../contexts/GridContext';
import Slider from 'rc-slider';
import { updateWidgetSettings } from '../../utils/settingsManager';

/**
 * ServoWidget - A grid widget for controlling a single servo motor
 * 
 * @component
 * @param {Object} props - Component props
 * @param {number} props.servoId - ID of the servo to control
 * @param {number} props.position - Last saved position (optional)
 * @param {number} props.speed - Speed of servo movement (optional)
 * @param {string} props.i - Widget ID in grid layout
 */
const ServoWidget = ({ servoId, position: savedPosition, speed: savedSpeed, i }) => {
  const { availableServos } = useAppContext();
  const { isEditable, updateWidgetProps } = useGridContext();
  const [position, setPosition] = useState(savedPosition || 0);
  const [speed, setSpeed] = useState(savedSpeed || 100);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(180);
  const [servoInfo, setServoInfo] = useState(null);
  
  // Find the servo data from available servos
  useEffect(() => {
    if (availableServos && availableServos.length > 0) {
      // Ensure we're comparing the same types
      const targetId = parseInt(servoId);
      
      // Flexible matching with type conversion
      const servo = availableServos.find(s => {
        const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
        return currentId === targetId;
      });
      
      if (servo) {
        setServoInfo(servo);
        setPosition(servo.position || 0);
        setSpeed(servo.speed || 100);
        setMin(servo.min_pos || 0);
        setMax(servo.max_pos || 180);
      }
    }
  }, [availableServos, servoId]);
  
  // Listen for servo updates from WebSocket
  useEffect(() => {
    const unsubscribe = node.on('servo_status', (event) => {
      if (event && event.value) {
        const servos = event.value || [];
        
        // Ensure we're comparing the same types
        const targetId = parseInt(servoId);
        
        // Flexible matching with type conversion
        const servo = servos.find(s => {
          const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
          return currentId === targetId;
        });
        
        if (servo) {
          setServoInfo(servo);
          setPosition(servo.position || 0);
          setSpeed(servo.speed || 100);
          setMin(servo.min_pos !== undefined ? servo.min_pos : 0);
          setMax(servo.max_pos !== undefined ? servo.max_pos : 180);
        }
      }
    });
    
    // Add button flash event listener
    const handleButtonFlash = (event) => {
      const { control } = event.detail;
      // Check if this is a flashable control that affects our servo
      const servoElement = document.querySelector(`[data-servo-id="${servoId}"]`);
      if (servoElement) {
        servoElement.classList.add('button-flash');
        setTimeout(() => {
          servoElement.classList.remove('button-flash');
        }, 300);
      }
    };
    
    window.addEventListener('gamepad_button_flash', handleButtonFlash);
    
    // Request servo data on mount
    node.emit('SCAN', []);
    
    return () => {
      unsubscribe();
      window.removeEventListener('gamepad_button_flash', handleButtonFlash);
    };
  }, [servoId]);

  // Handle position updates
  const handlePositionUpdate = (newPosition) => {
    const positionValue = parseInt(newPosition);
    setPosition(positionValue);
    
    // Send command to servo
    node.emit('set_servo', [parseInt(servoId), positionValue, parseInt(speed)]);
    
    // Save position in widget settings
    if (i) {
      updateWidgetSettings(i, { position: positionValue }, updateWidgetProps);
    }
  };
  
  // Handle speed updates
  const handleSpeedUpdate = (newSpeed) => {
    const speedValue = parseInt(newSpeed);
    setSpeed(speedValue);
    
    // Save speed in widget settings
    if (i) {
      updateWidgetSettings(i, { speed: speedValue }, updateWidgetProps);
    }
  };
  
  return (
    <div className="simple-slider-container" data-servo-id={servoId}>
      <Slider
        value={position}
        min={min}
        max={max}
        onChange={handlePositionUpdate}
        railStyle={{ backgroundColor: 'rgba(0,0,0,0.3)', height: 8, borderRadius: '4px' }}
        trackStyle={{ backgroundColor: 'var(--primary)', height: 8, borderRadius: '4px' }}
        handleStyle={{
          borderColor: 'var(--primary)',
          height: 24,
          width: 24,
          marginTop: -8,
          backgroundColor: '#222',
          boxShadow: '0 2px 5px rgba(0, 0, 0, 0.5)',
          border: '2px solid var(--primary)'
        }}
      />
      {isEditable && (
        <div className="position-display">{position}</div>
      )}
    </div>
  );
};

export default ServoWidget;