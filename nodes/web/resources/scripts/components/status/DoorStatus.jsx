/**
 * DoorStatus Component
 * 
 * Displays a clickable status indicator showing whether the front door is open or closed
 * based on the "Door" servo position. Uses a door icon that is gray when closed
 * and yellow when open. Clicking the icon toggles the door between open/closed positions.
 * 
 * @component
 */
import React, { useState, useEffect } from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import { useAppContext } from '../../contexts/AppContext';
import { statusIconStyles } from './StatusIconStyles';
import node from '../../Node';

const DoorStatus = () => {
  const { availableServos } = useAppContext();
  const [isOpen, setIsOpen] = useState(false);
  const [doorServo, setDoorServo] = useState(null);
  
  // Monitor door servo position to determine if door is open or closed
  useEffect(() => {
    // Find the servo with alias "Door"
    const servo = availableServos.find(servo => servo.alias === "Door");
    
    if (servo) {
      setDoorServo(servo);
      // Determine door state based on servo position
      // 700 is closed, 1023 is open
      // Use midpoint as threshold with some buffer
      const doorIsOpen = servo.position > 850;
      setIsOpen(doorIsOpen);
    }
  }, [availableServos]);
  
  // Handle door toggle click
  const handleDoorToggle = () => {
    if (!doorServo) return;
    
    // Toggle between closed (700) and open (1023) positions
    const targetPosition = isOpen ? 700 : 1023;
    const speed = 100; // Default speed
    
    // Send command to servo using the servo ID (same format as ServoDebugView)
    node.emit('move_servo', [{id: doorServo.id, position: targetPosition}]);
  };
  
  return (
    <Tooltip
      label={isOpen ? "Front door is open - click to close" : "Front door is closed - click to open"} 
      position="bottom"
      withArrow
    >
      <ActionIcon 
        variant="transparent" 
        radius="xl"
        aria-label="Door Status"
        style={{
          ...statusIconStyles.actionIcon,
          cursor: doorServo ? 'pointer' : 'default'
        }}
        onClick={handleDoorToggle}
        disabled={!doorServo}
      >
        <i 
          className={`fa-solid ${isOpen ? 'fa-door-open' : 'fa-door-closed'}`}
          style={{ 
            color: isOpen ? 'var(--mantine-color-amber-6)' : 'var(--mantine-color-gray-6)',
            ...statusIconStyles.icon
          }}
        ></i>
      </ActionIcon>
    </Tooltip>
  );
};

export default DoorStatus;