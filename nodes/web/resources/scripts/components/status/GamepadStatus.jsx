/**
 * GamepadStatus Component
 * 
 * Displays a status indicator showing connected gamepads.
 * Shows a dropdown with a list of connected gamepads and links to the gamepad debug view.
 * 
 * @component
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Menu, 
  ActionIcon, 
  Badge, 
  Text, 
  Stack, 
  Box 
} from '@mantine/core';

const GamepadStatus = () => {
  const [gamepads, setGamepads] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  
  useEffect(() => {
    const checkGamepads = () => {
      const connectedGamepads = navigator.getGamepads();
      const gamepadArray = [];
      
      for (let i = 0; i < connectedGamepads.length; i++) {
        if (connectedGamepads[i]) {
          gamepadArray.push({
            index: i,
            id: connectedGamepads[i].id
          });
        }
      }
      
      setGamepads(gamepadArray);
    };
    
    // Check initially
    checkGamepads();
    
    // Add event listeners for gamepad connection/disconnection
    window.addEventListener('gamepadconnected', checkGamepads);
    window.addEventListener('gamepaddisconnected', checkGamepads);
    
    // Poll for gamepad updates
    const interval = setInterval(checkGamepads, 1000);
    
    return () => {
      window.removeEventListener('gamepadconnected', checkGamepads);
      window.removeEventListener('gamepaddisconnected', checkGamepads);
      clearInterval(interval);
    };
  }, []);
  
  // Format the gamepad name with minimal processing
  const formatGamepadName = (id) => {
    // Just do basic cleanup but preserve the full name
    let name = id
      .replace('Vendor: ', '')
      .replace('Product: ', '')
      .split('(')[0]
      .replace(/\s+/g, ' ')
      .trim();
    
    // If we got an empty name after cleanup, use a generic name
    if (!name) {
      name = 'Game Controller';
    }
    
    return name;
  };
  
  return (
    <Menu
      opened={isOpen}
      onChange={setIsOpen}
      position="bottom-end"
      shadow="md"
      width={220}
      withArrow
    >
      <Menu.Target>
        <ActionIcon
          variant="transparent"
          radius="xl"
          aria-label="Gamepads"
          onClick={() => setIsOpen(!isOpen)}
        >
          <Box pos="relative">
            <i 
              className="fa-solid fa-gamepad" 
              style={{ 
                color: gamepads.length > 0 
                  ? 'var(--mantine-color-amber-6)' 
                  : 'var(--mantine-color-gray-6)'
              }}
            ></i>
            {gamepads.length > 0 && (
              <Badge 
                size="xs" 
                color="amber" 
                variant="filled"
                style={{
                  position: 'absolute',
                  top: -6,
                  right: -6,
                  padding: '0 4px',
                  minWidth: '16px',
                  height: '16px'
                }}
              >
                {gamepads.length}
              </Badge>
            )}
          </Box>
        </ActionIcon>
      </Menu.Target>
      
      <Menu.Dropdown>
        {gamepads.length > 0 ? (
          gamepads.map(gamepad => (
            <Menu.Item
              key={gamepad.index}
              component={Link}
              to={`/gamepad/${gamepad.index}`}
              leftSection={
                <i 
                  className="fa-solid fa-gamepad" 
                  style={{ color: 'var(--mantine-color-amber-6)' }}
                ></i>
              }
            >
              <div>
                <Text size="sm" style={{ lineHeight: 1.2 }}>{formatGamepadName(gamepad.id)}</Text>
                <Text size="xs" c="dimmed" style={{ lineHeight: 1.2 }}>Controller #{gamepad.index}</Text>
              </div>
            </Menu.Item>
          ))
        ) : (
          <Menu.Item
            disabled
            leftSection={<i className="fa-solid fa-circle-exclamation"></i>}
          >
            <Text size="sm">No gamepads connected</Text>
          </Menu.Item>
        )}
      </Menu.Dropdown>
    </Menu>
  );
};

export default GamepadStatus;