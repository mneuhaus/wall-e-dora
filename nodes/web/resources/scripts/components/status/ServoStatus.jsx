/**
 * ServoStatus Component
 * 
 * Displays a dropdown menu with the current status of all connected servos.
 * Shows servo ID and current position, with links to the servo debug view.
 * Can be clicked to refresh the servo status.
 * 
 * @component
 */
import React, { useState, useEffect } from 'react';
import { 
  Menu, 
  ActionIcon, 
  Badge, 
  Group, 
  Text, 
  Box, 
  Stack, 
  UnstyledButton 
} from '@mantine/core';
import { useAppContext } from '../../contexts/AppContext';
import { Link } from 'react-router-dom';
import node from '../../Node';

const ServoStatus = () => {
  const { availableServos } = useAppContext();
  const [servos, setServos] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  
  // Direct connection to node events for more reliable updates
  useEffect(() => {
    const unsubscribe = node.on('servo_status', (event) => {
      if (event && event.value) {
        setServos(event.value);
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, []);
  
  // Use either direct event data or context data
  const servoData = servos.length > 0 ? servos : (availableServos || []);
  
  const handleOpenMenu = () => {
    // Request fresh data when opening menu
    node.emit('SCAN', []);
    setIsOpen(true);
  };
  
  return (
    <Menu 
      opened={isOpen} 
      onChange={setIsOpen}
      onOpen={handleOpenMenu}
      position="bottom-end"
      shadow="md"
      width={220}
      withArrow
    >
      <Menu.Target>
        <ActionIcon
          variant="transparent"
          radius="xl"
          aria-label="Servos"
        >
          <i 
            className="fa-solid fa-gears" 
            style={{ 
              color: servoData.length > 0 
                ? 'var(--mantine-color-amber-6)' 
                : 'var(--mantine-color-gray-6)'
            }}
          ></i>
        </ActionIcon>
      </Menu.Target>
      
      <Menu.Dropdown>
        {servoData.length > 0 ? (
          servoData.map(servo => (
            <Menu.Item
              key={servo.id}
              component={Link}
              to={`/servo/${servo.id}`}
              leftSection={
                <i 
                  className="fa-solid fa-gear" 
                  style={{ color: 'var(--mantine-color-amber-6)' }}
                ></i>
              }
            >
              <div>
                <Text size="sm" style={{ lineHeight: 1.2 }}>Servo #{servo.id}</Text>
                <Text size="xs" c="dimmed" style={{ lineHeight: 1.2 }}>Position: {servo.position || 0}</Text>
              </div>
            </Menu.Item>
          ))
        ) : (
          <Menu.Item
            disabled
            leftSection={<i className="fa-solid fa-gear"></i>}
          >
            <Text size="sm">No servos connected</Text>
          </Menu.Item>
        )}
      </Menu.Dropdown>
    </Menu>
  );
};

export default ServoStatus;