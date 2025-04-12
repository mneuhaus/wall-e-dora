/**
 * DoorStatus Component
 * 
 * Displays a status indicator showing whether the front door is open or closed
 * based on the "Door" servo position. Uses a door icon that is gray when closed
 * and yellow when open.
 * 
 * @component
 */
import React, { useState, useEffect } from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import { useAppContext } from '../../contexts/AppContext';
import { statusIconStyles } from './StatusIconStyles';

const DoorStatus = () => {
  const { availableServos } = useAppContext();
  const [isOpen, setIsOpen] = useState(false);
  
  // Monitor door servo position to determine if door is open or closed
  useEffect(() => {
    // Find the servo with alias "Door"
    const doorServo = availableServos.find(servo => servo.alias === "Door");
    
    if (doorServo) {
      // Determine door state based on servo position
      // 700 is closed, 1023 is open
      // Use midpoint as threshold with some buffer
      const doorIsOpen = doorServo.position > 850;
      setIsOpen(doorIsOpen);
    }
  }, [availableServos]);
  
  return (
    <Tooltip
      label={isOpen ? "Front door is open" : "Front door is closed"} 
      position="bottom"
      withArrow
    >
      <ActionIcon 
        variant="transparent" 
        radius="xl"
        aria-label="Door Status"
        style={statusIconStyles.actionIcon}
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