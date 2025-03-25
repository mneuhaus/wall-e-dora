import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import node from '../Node';
import gamepads from '../Gamepads';
import { keyframes, css } from '@emotion/css';
import GamepadMappingDialog from '../components/gamepad/GamepadMappingDialog';

// Mantine imports
import {
  Container,
  Paper,
  Title,
  Text,
  Group,
  Stack,
  Grid,
  Table,
  Box,
  ActionIcon,
  Button,
  rem
} from '@mantine/core';

/**
 * GamepadView Component
 * 
 * Displays detailed information about a connected gamepad.
 * Shows all buttons, axes, and control states for the selected gamepad.
 * Provides mapping functionality to create custom control profiles.
 * 
 * @component
 */
const GamepadView = () => {
  const { index } = useParams();
  const [, forceUpdate] = useState({});
  const [gamepadInstance, setGamepadInstance] = useState(null);
  const [prevValues, setPrevValues] = useState({});
  const [flashingControls, setFlashingControls] = useState({});
  const [isMapDialogOpen, setIsMapDialogOpen] = useState(false);
  
  // Force re-render function that we'll register with the gamepad
  const handleForceUpdate = useCallback(() => {
    forceUpdate({});
  }, []);
  
  // Define a direct animation style for flashing
  const getFlashStyle = () => ({
    animation: 'flash-animation 300ms ease',
    position: 'relative',
    animationName: 'flash-animation'
  });

  // Add the keyframes rule to the document if it doesn't exist yet
  useEffect(() => {
    if (!document.getElementById('flash-keyframes')) {
      const style = document.createElement('style');
      style.id = 'flash-keyframes';
      style.innerHTML = `
        @keyframes flash-animation {
          0% { background-color: rgba(255, 179, 0, 0.3); }
          100% { background-color: transparent; }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);
  
  // Track previous values to detect changes
  useEffect(() => {
    if (!gamepadInstance) return;
    
    // Add some debug logging occasionally
    const shouldLog = Math.random() < 0.05;
    if (shouldLog) {
      console.log('GamepadView: Checking for control changes', gamepadInstance.id);
    }
    
    // Check each control for changes
    const newFlashingControls = {};
    const newPrevValues = { ...prevValues };
    
    // Tolerance threshold for analog controls to prevent false positives
    const ANALOG_THRESHOLD = 0.05;
    const BUTTON_THRESHOLD = 0.1; // Lower threshold for buttons
    
    // Check all gamepad controls for changes
    Object.keys(gamepadInstance).forEach(key => {
      // Skip non-control properties
      if (key === 'id' || key === 'index' || key === 'api' || 
          key === 'emitter' || key === '_forceUpdateHandlers' || 
          key === 'pollIntervalId' || key === 'servoMapping' || 
          key === 'axes' || key === 'buttons') {
        return;
      }
      
      const control = gamepadInstance[key];
      if (control && typeof control === 'object' && 'value' in control) {
        const currentValue = parseFloat(control.value);
        const previousValue = parseFloat(prevValues[key] || 0);
        
        // Check if the value has changed significantly
        const isAnalog = key.includes('STICK') || key === 'LEFT_SHOULDER_BOTTOM' || key === 'RIGHT_SHOULDER_BOTTOM';
        const threshold = isAnalog ? ANALOG_THRESHOLD : BUTTON_THRESHOLD;
        
        // For buttons, we just care if they're pressed at all (state change)
        const isActive = isAnalog ? Math.abs(currentValue) > threshold : currentValue > threshold;
        const wasActive = isAnalog ? Math.abs(previousValue) > threshold : previousValue > threshold;
        
        // Flash when a button is pressed or an axis moves past the threshold
        if (isActive && !wasActive) {
          console.log(`Control ${key} became active: ${currentValue}`);
          newFlashingControls[key] = true;
          
          // Schedule removal of flash after animation completes
          setTimeout(() => {
            setFlashingControls(prev => {
              const updated = { ...prev };
              delete updated[key];
              return updated;
            });
          }, 300); // Match the animation duration
        }
        
        // Update previous value
        newPrevValues[key] = currentValue;
      }
    });
    
    // Update state with new flashing controls and previous values
    if (Object.keys(newFlashingControls).length > 0) {
      setFlashingControls(prev => ({ ...prev, ...newFlashingControls }));
    }
    setPrevValues(newPrevValues);
  }, [gamepadInstance]); // Keep just gamepadInstance to avoid infinite loop
  
  useEffect(() => {
    // Set initial gamepad if available
    if (gamepads.gamepads[index]) {
      setGamepadInstance(gamepads.gamepads[index]);
      
      // Register for force updates when gamepad data changes
      const unregister = gamepads.gamepads[index].registerForceUpdate(handleForceUpdate);
      
      return () => {
        // Clean up
        unregister();
      };
    }
    
    // Listen for gamepad connection
    const handleGamepadConnected = (connectedGamepad) => {
      if (connectedGamepad.index === parseInt(index)) {
        setGamepadInstance(connectedGamepad);
        
        // Register for force updates
        const unregister = connectedGamepad.registerForceUpdate(handleForceUpdate);
        
        // Clean up previous registration if component unmounts before this cleanup runs
        return () => {
          unregister();
        };
      }
    };
    
    // Set up event listener
    gamepads.on('gamepadconnected', handleGamepadConnected);
    
    return () => {
      // Clean up event listener
      gamepads.off('gamepadconnected', handleGamepadConnected);
    };
  }, [index, handleForceUpdate]);
  
  if (!gamepadInstance) {
    return (
      <Container size="xl" py="md">
        <Paper p="md" radius="md" withBorder>
          <Group mb="md">
            <ActionIcon component={Link} to="/" variant="subtle" color="amber" radius="xl">
              <i className="fa-solid fa-arrow-left"></i>
            </ActionIcon>
            <Title order={4}>Gamepad {index} Not Connected</Title>
          </Group>
          <Text>Please connect a gamepad and make sure it's recognized by the browser.</Text>
        </Paper>
      </Container>
    );
  }
  
  // Helper function to render a control row with flash animation
  const renderControlRow = (controlName, controlValue) => {
    const isFlashing = flashingControls[controlName];
    
    return (
      <Table.Tr 
        key={controlName}
        style={isFlashing ? getFlashStyle() : {}}
      >
        <Table.Td style={{ fontWeight: 500, color: 'var(--mantine-color-dimmed)' }}>
          {controlName}
        </Table.Td>
        <Table.Td style={{ color: 'var(--mantine-color-amber-filled)', textAlign: 'right' }}>
          {controlValue !== undefined ? controlValue : 'N/A'}
        </Table.Td>
        <Table.Td style={{ textAlign: 'right' }}>
          {gamepadInstance.customMapping?.mapping?.[controlName] ? (
            <>
              {gamepadInstance.customMapping.mapping[controlName].type === 'button' ? 'Button' : 'Axis'} 
              #{gamepadInstance.customMapping.mapping[controlName].index}
            </>
          ) : 'Not mapped'}
        </Table.Td>
      </Table.Tr>
    );
  };
  
  // Group gamepad controls by category for better organization
  const analogControls = [
    { name: 'LEFT_ANALOG_STICK_X', value: gamepadInstance.LEFT_ANALOG_STICK_X?.value },
    { name: 'LEFT_ANALOG_STICK_Y', value: gamepadInstance.LEFT_ANALOG_STICK_Y?.value },
    { name: 'RIGHT_ANALOG_STICK_X', value: gamepadInstance.RIGHT_ANALOG_STICK_X?.value },
    { name: 'RIGHT_ANALOG_STICK_Y', value: gamepadInstance.RIGHT_ANALOG_STICK_Y?.value },
    { name: 'DPAD_UP', value: gamepadInstance.DPAD_UP?.value },
    { name: 'DPAD_DOWN', value: gamepadInstance.DPAD_DOWN?.value },
    { name: 'DPAD_LEFT', value: gamepadInstance.DPAD_LEFT?.value },
    { name: 'DPAD_RIGHT', value: gamepadInstance.DPAD_RIGHT?.value }
  ];
  
  const faceControls = [
    { name: 'FACE_1', value: gamepadInstance.FACE_1?.value },
    { name: 'FACE_2', value: gamepadInstance.FACE_2?.value },
    { name: 'FACE_3', value: gamepadInstance.FACE_3?.value },
    { name: 'FACE_4', value: gamepadInstance.FACE_4?.value },
    { name: 'LEFT_SHOULDER', value: gamepadInstance.LEFT_SHOULDER?.value },
    { name: 'RIGHT_SHOULDER', value: gamepadInstance.RIGHT_SHOULDER?.value },
    { name: 'LEFT_SHOULDER_BOTTOM', value: gamepadInstance.LEFT_SHOULDER_BOTTOM?.value },
    { name: 'RIGHT_SHOULDER_BOTTOM', value: gamepadInstance.RIGHT_SHOULDER_BOTTOM?.value }
  ];
  
  const specialControls = [
    { name: 'SELECT', value: gamepadInstance.SELECT?.value },
    { name: 'START', value: gamepadInstance.START?.value },
    { name: 'LEFT_ANALOG_BUTTON', value: gamepadInstance.LEFT_ANALOG_BUTTON?.value },
    { name: 'RIGHT_ANALOG_BUTTON', value: gamepadInstance.RIGHT_ANALOG_BUTTON?.value },
    { name: 'HOME', value: gamepadInstance.HOME?.value },
    { name: 'MISCBUTTON_1', value: gamepadInstance.MISCBUTTON_1?.value },
    { name: 'MISCBUTTON_2', value: gamepadInstance.MISCBUTTON_2?.value }
  ];
  
  return (
    <Container size="xl" py="md">
      <Paper radius="md" withBorder p={0}>
        {/* Header Section */}
        <Box py="xs" px="md" bg="rgba(255, 215, 0, 0.05)" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <Group position="apart">
            <Group>
              <ActionIcon component={Link} to="/" variant="subtle" color="amber" radius="xl">
                <i className="fa-solid fa-arrow-left"></i>
              </ActionIcon>
              <Title order={5}>{gamepadInstance.id}</Title>
            </Group>
            <Button 
              variant="outline" 
              color="amber" 
              leftIcon={<i className="fa-solid fa-gamepad"></i>}
              onClick={() => setIsMapDialogOpen(true)}
            >
              Map Controls
            </Button>
          </Group>
        </Box>
        
        <Box p="md">
          <Grid gutter="md">
            {/* Analog Controls Card */}
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Paper radius="md" withBorder shadow="sm" h="100%" style={{ display: 'flex', flexDirection: 'column' }}>
                <Box 
                  py="xs" 
                  px="md" 
                  bg="rgba(255, 215, 0, 0.05)" 
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <Group>
                    <i className="fa-solid fa-gamepad" style={{ color: '#FFB300' }}></i>
                    <Title order={6} c="amber" style={{ marginTop: 0 }}>Analog Controls</Title>
                  </Group>
                </Box>
                
                <Box p="xs" style={{ flex: 1 }}>
                  <Table striped highlightOnHover withTableBorder withColumnBorders>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Control</Table.Th>
                        <Table.Th style={{ textAlign: 'right' }}>Value</Table.Th>
                        <Table.Th style={{ textAlign: 'right' }}>Mapped To</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {analogControls.map((control) => 
                        renderControlRow(control.name, control.value)
                      )}
                    </Table.Tbody>
                  </Table>
                </Box>
              </Paper>
            </Grid.Col>
            
            {/* Face Buttons Card */}
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Paper radius="md" withBorder shadow="sm" h="100%" style={{ display: 'flex', flexDirection: 'column' }}>
                <Box 
                  py="xs" 
                  px="md" 
                  bg="rgba(255, 215, 0, 0.05)" 
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <Group>
                    <i className="fa-solid fa-circle" style={{ color: '#FFB300' }}></i>
                    <Title order={6} c="amber" style={{ marginTop: 0 }}>Face Buttons</Title>
                  </Group>
                </Box>
                
                <Box p="xs" style={{ flex: 1 }}>
                  <Table striped highlightOnHover withTableBorder withColumnBorders>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Control</Table.Th>
                        <Table.Th style={{ textAlign: 'right' }}>Value</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {faceControls.map((control) => 
                        renderControlRow(control.name, control.value)
                      )}
                    </Table.Tbody>
                  </Table>
                </Box>
              </Paper>
            </Grid.Col>
            
            {/* Special Buttons Card */}
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Paper radius="md" withBorder shadow="sm" h="100%" style={{ display: 'flex', flexDirection: 'column' }}>
                <Box 
                  py="xs" 
                  px="md" 
                  bg="rgba(255, 215, 0, 0.05)" 
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <Group>
                    <i className="fa-solid fa-star" style={{ color: '#FFB300' }}></i>
                    <Title order={6} c="amber" style={{ marginTop: 0 }}>Special Buttons</Title>
                  </Group>
                </Box>
                
                <Box p="xs" style={{ flex: 1 }}>
                  <Table striped highlightOnHover withTableBorder withColumnBorders>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Control</Table.Th>
                        <Table.Th style={{ textAlign: 'right' }}>Value</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {specialControls.map((control) => 
                        renderControlRow(control.name, control.value)
                      )}
                    </Table.Tbody>
                  </Table>
                </Box>
              </Paper>
            </Grid.Col>
          </Grid>
        </Box>
      </Paper>

      {/* Mapping Dialog */}
      <GamepadMappingDialog
        isOpen={isMapDialogOpen}
        onClose={() => setIsMapDialogOpen(false)}
        gamepad={gamepadInstance}
        gamepadIndex={parseInt(index)}
      />
    </Container>
  );
};

export default GamepadView;
