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
  Tooltip,
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
    animation: 'gamepad-flash 500ms ease-out',
    position: 'relative',
    zIndex: 10
  });

  // Add the keyframes rule to the document if it doesn't exist yet
  useEffect(() => {
    if (!document.getElementById('gamepad-flash-keyframes')) {
      const style = document.createElement('style');
      style.id = 'gamepad-flash-keyframes';
      style.innerHTML = `
        @keyframes gamepad-flash {
          0% { background-color: rgba(255, 179, 0, 0.5); }
          50% { background-color: rgba(255, 179, 0, 0.3); }
          100% { background-color: rgba(255, 179, 0, 0); }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);
  
  // Listen for gamepad button flash events
  useEffect(() => {
    const handleButtonFlash = (event) => {
      const { control, type, index } = event.detail;
      console.log(`Flash event: ${type} ${index} (${control})`);
      
      // Manually add flash for the control
      setFlashingControls(prev => ({
        ...prev,
        [control]: true
      }));
      
      // Clear after animation completes
      setTimeout(() => {
        setFlashingControls(prev => {
          const updated = { ...prev };
          delete updated[control];
          return updated;
        });
      }, 300);
    };
    
    window.addEventListener('gamepad_button_flash', handleButtonFlash);
    
    return () => {
      window.removeEventListener('gamepad_button_flash', handleButtonFlash);
    };
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
        // Identify analog controls for proper threshold detection
        const isAnalog = key.includes('STICK') || 
                         key === 'LEFT_SHOULDER_BOTTOM' || 
                         key === 'RIGHT_SHOULDER_BOTTOM' ||
                         (gamepadInstance.customMapping?.mapping?.[key]?.type === 'axis');
        
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
    const isMapped = gamepadInstance.customMapping?.mapping?.[controlName];
    const control = gamepadInstance[controlName];
    
    // Process control for display
    
    // Only show mapped controls if custom mapping exists
    if (gamepadInstance.customMapping && !isMapped) {
      return null;
    }
    
    // Determine if a control is analog (has range of values) or digital (0/1)
    const isAnalog = () => {
      // Check if control values are frequently between 0 and 1 
      if (!control) return false;
      
      // Use the isAnalog property from mapping if available
      if (isMapped && isMapped.isAnalog !== undefined) {
        return isMapped.isAnalog;
      }
      
      // Fallback for legacy mappings that don't have isAnalog property
      
      // Explicitly known analog controls
      if (
        controlName.includes('STICK') || 
        controlName === 'LEFT_SHOULDER_BOTTOM' || 
        controlName === 'RIGHT_SHOULDER_BOTTOM'
      ) {
        return true;
      }
      
      // Check if the raw mapping is an axis type
      if (isMapped && isMapped.type === 'axis') {
        return true;
      }
      
      // Check for non-binary values (if value is between 0.1 and 0.9)
      const value = parseFloat(control.value || 0);
      return value > 0.1 && value < 0.9;
    };
    
    // Create tooltip text for the raw input with additional analog/digital info
    const getTooltip = () => {
      if (!isMapped) return '';
      
      const inputType = isMapped.type === 'button' ? 'Button' : 'Axis';
      const controlType = isAnalog() ? 'Analog' : 'Digital';
      
      return `${inputType} #${isMapped.index} (${controlType})`;
    };
    
    return (
      <Table.Tr 
        key={controlName}
        style={isFlashing ? getFlashStyle() : {}}
      >
        <Table.Td style={{ fontWeight: 500, color: 'var(--mantine-color-dimmed)' }}>
          {isMapped ? (
            <Tooltip 
              label={getTooltip()} 
              position="top-start"
              withArrow
              arrowSize={6}
              offset={-2}
              color="dark"
              transitionProps={{ transition: 'pop', duration: 200 }}
            >
              <Group spacing="xs" align="center" nowrap>
                <span>{controlName}</span>
                {isAnalog() && (
                  <Text size="xs" c="dimmed" style={{ marginLeft: rem(4) }}>
                    <i className="fa-solid fa-sliders" style={{ fontSize: rem(10) }}></i>
                  </Text>
                )}
              </Group>
            </Tooltip>
          ) : (
            <Group spacing="xs" align="center" nowrap>
              <span>{controlName}</span>
              {isAnalog() && (
                <Text size="xs" c="dimmed" style={{ marginLeft: rem(4) }}>
                  <i className="fa-solid fa-sliders" style={{ fontSize: rem(10) }}></i>
                </Text>
              )}
            </Group>
          )}
        </Table.Td>
        <Table.Td style={{ color: 'var(--mantine-color-amber-filled)', textAlign: 'right' }}>
          {controlValue !== undefined ? 
            (isAnalog() ? 
              // Format analog values with decimal precision
              parseFloat(controlValue).toFixed(2) : 
              // For digital controls, display as 0 or 1
              (parseFloat(controlValue) > 0 ? '1' : '0')
            ) : 
            'N/A'}
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
      <Paper radius="md" withBorder p={0} shadow="md">
        {/* Header Section */}
        <Box py="xs" px="md" bg="rgba(255, 179, 0, 0.08)" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', borderTopLeftRadius: 'var(--mantine-radius-md)', borderTopRightRadius: 'var(--mantine-radius-md)' }}>
          <Group justify="space-between">
            <Group>
              <ActionIcon component={Link} to="/" variant="subtle" color="amber" radius="xl" size="lg">
                <i className="fa-solid fa-arrow-left"></i>
              </ActionIcon>
              <div>
                {/* Extract a better name from gamepad ID */}
                <Title order={4} c="amber">
                  {gamepadInstance.id.split('(')[0].trim() || "Gamepad"}
                </Title>
                <Text size="sm" c="dimmed">
                  {gamepadInstance.id.match(/Vendor:\s*([0-9a-fA-F]+).*Product:\s*([0-9a-fA-F]+)/) 
                    ? `ID: ${gamepadInstance.id.match(/Vendor:\s*([0-9a-fA-F]+)/)[1]}:${gamepadInstance.id.match(/Product:\s*([0-9a-fA-F]+)/)[1]}`
                    : `Index: ${gamepadInstance.index}`
                  }
                </Text>
              </div>
            </Group>
            <Tooltip label="Create Mapping" withArrow position="left">
              <ActionIcon
                color="amber"
                variant="subtle"
                radius="xl"
                size="lg"
                onClick={() => setIsMapDialogOpen(true)}
              >
                <i className="fa-solid fa-wand-magic-sparkles"></i>
              </ActionIcon>
            </Tooltip>
          </Group>
        </Box>
        
        <Box p="md">
          <Grid gutter="md">
            {/* Analog Controls Column */}
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Box mb={15}>
                <Box mb="xs" px="xs">
                  <Title order={5} c="amber" style={{ marginTop: 0 }}>Analog Controls</Title>
                </Box>
                
                <Table striped highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Control</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Value</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {analogControls.map((control) => 
                      renderControlRow(control.name, control.value)
                    )}
                  </Table.Tbody>
                </Table>
              </Box>
            </Grid.Col>
            
            {/* Face Buttons Column */}
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Box mb={15}>
                <Box mb="xs" px="xs">
                  <Title order={5} c="amber" style={{ marginTop: 0 }}>Face Buttons</Title>
                </Box>
                
                <Table striped highlightOnHover withTableBorder>
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
            </Grid.Col>
            
            {/* Special Buttons Column */}
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Box mb={15}>
                <Box mb="xs" px="xs">
                  <Title order={5} c="amber" style={{ marginTop: 0 }}>Special Buttons</Title>
                </Box>
                
                <Table striped highlightOnHover withTableBorder>
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
