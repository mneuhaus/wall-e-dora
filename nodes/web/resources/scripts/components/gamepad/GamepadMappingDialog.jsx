import React, { useState, useEffect, useRef } from 'react';
import node from '../../Node';
import { useAppContext } from '../../contexts/AppContext';

import {
  Modal,
  Box,
  Button,
  Group,
  Stack,
  Text,
  Title,
  Progress,
  Alert,
  Paper,
  Badge,
  Stepper,
  Grid,
} from '@mantine/core';

/**
 * GamepadMappingDialog - A simplified component for mapping gamepad controls
 */
const GamepadMappingDialog = ({ isOpen, onClose, gamepad, gamepadIndex }) => {
  // Basic state
  const [step, setStep] = useState(0);
  const [mapping, setMapping] = useState({});
  const [profileName, setProfileName] = useState('');
  const [currentControl, setCurrentControl] = useState(null);
  const [detectedControl, setDetectedControl] = useState(null);
  const [pressCount, setPressCount] = useState(0);
  const [showSuccess, setShowSuccess] = useState(false);
  const { isConnected } = useAppContext();
  
  // References
  const currentControlRef = useRef(currentControl);
  const isOpenRef = useRef(isOpen);
  const pollingRef = useRef(null);
  const prevInputs = useRef({ buttons: [], axes: [] });
  
  // Controls to map
  const controlsToMap = [
    { id: 'FACE_1', name: 'Face Button 1 (A/Cross)', type: 'button' },
    { id: 'FACE_2', name: 'Face Button 2 (B/Circle)', type: 'button' },
    { id: 'FACE_3', name: 'Face Button 3 (X/Square)', type: 'button' },
    { id: 'FACE_4', name: 'Face Button 4 (Y/Triangle)', type: 'button' },
    { id: 'LEFT_SHOULDER', name: 'Left Shoulder (LB)', type: 'button' },
    { id: 'RIGHT_SHOULDER', name: 'Right Shoulder (RB)', type: 'button' },
    { id: 'LEFT_SHOULDER_BOTTOM', name: 'Left Trigger (LT)', type: 'button' },
    { id: 'RIGHT_SHOULDER_BOTTOM', name: 'Right Trigger (RT)', type: 'button' },
    { id: 'SELECT', name: 'Select Button (Back/Share)', type: 'button' },
    { id: 'START', name: 'Start Button (Start/Options)', type: 'button' },
    { id: 'LEFT_ANALOG_BUTTON', name: 'Left Analog Stick Button (L3)', type: 'button' },
    { id: 'RIGHT_ANALOG_BUTTON', name: 'Right Analog Stick Button (R3)', type: 'button' },
    { id: 'DPAD_UP', name: 'D-Pad Up', type: 'button' },
    { id: 'DPAD_DOWN', name: 'D-Pad Down', type: 'button' },
    { id: 'DPAD_LEFT', name: 'D-Pad Left', type: 'button' },
    { id: 'DPAD_RIGHT', name: 'D-Pad Right', type: 'button' },
    { id: 'HOME', name: 'Home Button (Guide/PS)', type: 'button' },
    { id: 'LEFT_ANALOG_STICK_X', name: 'Left Analog Stick (X-Axis)', type: 'axis' },
    { id: 'LEFT_ANALOG_STICK_Y', name: 'Left Analog Stick (Y-Axis)', type: 'axis' },
    { id: 'RIGHT_ANALOG_STICK_X', name: 'Right Analog Stick (X-Axis)', type: 'axis' },
    { id: 'RIGHT_ANALOG_STICK_Y', name: 'Right Analog Stick (Y-Axis)', type: 'axis' },
  ];
  
  // Generate profile name from gamepad ID
  const makeProfileName = (gamepad) => {
    if (!gamepad) return 'Custom Gamepad Profile';
    
    // Extract vendor/product name if available
    const id = gamepad.id;
    let name = 'Unknown Gamepad';
    
    if (id.includes('Vendor:') || id.includes('Product:')) {
      const vendorMatch = id.match(/Vendor:\s*([^(]+)/);
      const productMatch = id.match(/Product:\s*([^(]+)/);
      name = (vendorMatch && vendorMatch[1] ? vendorMatch[1].trim() : '') + 
             (productMatch && productMatch[1] ? ' ' + productMatch[1].trim() : '');
    } else {
      // Try to extract a reasonable name from the ID
      name = id.split('(')[0].trim();
    }
    
    return name || 'Custom Gamepad Profile';
  };
  
  // Initialize when the dialog opens
  useEffect(() => {
    if (isOpen) {
      // Reset everything
      setStep(0);
      setMapping({});
      setPressCount(0);
      setDetectedControl(null);
      setShowSuccess(false);
      
      // Set first control to map
      setCurrentControl(controlsToMap[0]);
      
      // Set profile name
      setProfileName(makeProfileName(gamepad));
      
      // Start polling for inputs
      startPolling();
      
      console.log('Dialog opened, set currentControl to:', controlsToMap[0]?.id);
    } else {
      // Clean up
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
  }, [isOpen, gamepad]);

  useEffect(() => {
    currentControlRef.current = currentControl;
  }, [currentControl]);

  useEffect(() => {
    isOpenRef.current = isOpen;
  }, [isOpen]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, []);
  
  // Start polling for inputs
  const startPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    
    console.log('Starting input polling...');
    
    pollingRef.current = setInterval(() => {
      console.log('Polling iteration triggered');
      if (!isOpenRef.current || !currentControlRef.current) {
        console.log('Skipping poll (dialog closed or no control)');
        return;
      }
      
      const gamepads = navigator.getGamepads();
      if (!gamepads || !gamepads[gamepadIndex]) {
        return;
      }
      
      const gamepad = gamepads[gamepadIndex];
      detectInput(gamepad);
    }, 50);
  };
  
  // Detect button/axis inputs
  const detectInput = (gamepad) => {
    if (!gamepad || !currentControl) {
      console.log("detectInput: gamepad or currentControl is missing", gamepad, currentControl);
      return;
    }
    
    const isAxisMapping = currentControl.type === 'axis';
    const buttonThreshold = 0.2;
    const axisThreshold = 0.3;
    
    // Initialize previous values if needed
    if (prevInputs.current.buttons.length === 0) {
      prevInputs.current = {
        buttons: Array(gamepad.buttons.length).fill(0),
        axes: Array(gamepad.axes.length).fill(0)
      };
    }
    
    // Check all buttons
    for (let i = 0; i < gamepad.buttons.length; i++) {
      const buttonValue = gamepad.buttons[i].value;
      const prevValue = prevInputs.current.buttons[i];
      
      // For button mapping, detect new presses
      if (!isAxisMapping && buttonValue > buttonThreshold && prevValue <= buttonThreshold) {
        console.log(`Button ${i} pressed: ${buttonValue}`);
        recordInput('button', i);
      }
      
      // Update previous value
      prevInputs.current.buttons[i] = buttonValue;
    }
    
    // Check all axes
    for (let i = 0; i < gamepad.axes.length; i++) {
      const axisValue = gamepad.axes[i];
      const prevValue = prevInputs.current.axes[i];
      
      // For axis mapping, detect significant movements
      if (isAxisMapping && 
          (Math.abs(axisValue) > axisThreshold && Math.abs(prevValue) <= axisThreshold)) {
        console.log(`Axis ${i} moved: ${axisValue}`);
        recordInput('axis', i);
      }
      
      // Update previous value
      prevInputs.current.axes[i] = axisValue;
    }
  };
  
  // Record a detected input
  const recordInput = (type, index) => {
    console.log("recordInput called with", type, index);
    // Ignore wrong types
    if (currentControl.type === 'axis' && type !== 'axis') return;
    
    // Check if input changed
    if (detectedControl && (detectedControl.type !== type || detectedControl.index !== index)) {
      return;
    }
    
    // Record the input
    setDetectedControl({ type, index });
    
    // Increment press count
    setPressCount(prev => {
      const newCount = prev + 1;
      
      // If we have 3 presses, move to next control
      if (newCount >= 3) {
        // Save mapping
        setMapping(prev => ({
          ...prev,
          [currentControl.id]: { type, index }
        }));
        
        // Schedule move to next
        setTimeout(() => {
          goToNextControl();
        }, 1000);
      }
      
      return newCount;
    });
  };
  
  // Go to next control
  const goToNextControl = () => {
    const nextIndex = step + 1;
    
    if (nextIndex < controlsToMap.length) {
      setStep(nextIndex);
      setCurrentControl(controlsToMap[nextIndex]);
      setDetectedControl(null);
      setPressCount(0);
      console.log(`Moving to control ${nextIndex}: ${controlsToMap[nextIndex].id}`);
    } else {
      // All done, show summary
      setCurrentControl(null);
      console.log('Mapping complete, showing summary');
    }
  };
  
  // Skip current control
  const skipControl = () => {
    goToNextControl();
  };
  
  // Go back to previous control
  const goToPrevControl = () => {
    if (step > 0) {
      const prevIndex = step - 1;
      setStep(prevIndex);
      setCurrentControl(controlsToMap[prevIndex]);
      setDetectedControl(null);
      setPressCount(0);
      
      // Remove mapping
      if (mapping[controlsToMap[prevIndex].id]) {
        setMapping(prev => {
          const updated = { ...prev };
          delete updated[controlsToMap[prevIndex].id];
          return updated;
        });
      }
    }
  };
  
  // Save the profile
  const saveProfile = () => {
    const profileData = {
      id: gamepad.id,
      name: profileName,
      mapping: mapping
    };
    
    console.log('Saving profile:', profileData);
    node.emit('save_gamepad_profile', [profileData]);
    
    setShowSuccess(true);
    setTimeout(() => onClose(), 2000);
  };
  
  // Render mapping UI or summary
  const renderContent = () => {
    // Success message
    if (showSuccess) {
      return (
        <Alert color="green" title="Profile Saved!">
          Your gamepad mapping profile has been saved successfully.
        </Alert>
      );
    }
    
    // Mapping complete, show summary
    if (!currentControl && step >= controlsToMap.length) {
      return (
        <Stack spacing="md">
          <Title order={5} align="center">Mapping Complete!</Title>
          
          <Text>
            You've successfully mapped all controls for your gamepad. Review the
            mapping below and save your profile.
          </Text>
          
          <Paper p="md" withBorder>
            <Stack spacing="xs">
              <Text fw={500}>Profile Name</Text>
              <input
                type="text"
                value={profileName}
                onChange={(e) => setProfileName(e.target.value)}
                className="input"
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid var(--mantine-color-gray-4)',
                  background: 'var(--mantine-color-dark-7)',
                  color: 'var(--mantine-color-white)',
                }}
              />
              
              <Text fw={500} mt="md">Mapped Controls</Text>
              <Box style={{ maxHeight: '300px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid var(--mantine-color-gray-7)' }}>
                        Control
                      </th>
                      <th style={{ textAlign: 'right', padding: '8px', borderBottom: '1px solid var(--mantine-color-gray-7)' }}>
                        Mapped To
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {controlsToMap.map((control) => {
                      const mappedInput = mapping[control.id];
                      return (
                        <tr key={control.id} style={{ borderBottom: '1px solid var(--mantine-color-gray-8)' }}>
                          <td style={{ padding: '8px' }}>
                            {control.name}
                          </td>
                          <td style={{ textAlign: 'right', padding: '8px' }}>
                            {mappedInput ? (
                              <Badge color="amber">
                                {mappedInput.type === 'button' ? 'Button' : 'Axis'} #{mappedInput.index}
                              </Badge>
                            ) : (
                              <Badge color="gray" variant="outline">
                                Skipped
                              </Badge>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </Box>
            </Stack>
          </Paper>
          
          <Group position="right" mt="md">
            <Button color="gray" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button color="amber" onClick={saveProfile}>
              Save Profile
            </Button>
          </Group>
        </Stack>
      );
    }
    
    // Show mapping UI
    return (
      <Stack spacing="lg">
        <Stepper active={step} orientation="horizontal" color="amber">
          {[0, 1, 2].map((stepIndex) => (
            <Stepper.Step
              key={stepIndex}
              label={`Step ${stepIndex + 1}`}
              description={
                stepIndex === 0 ? "Buttons" :
                stepIndex === 1 ? "D-Pad" : "Sticks"
              }
            />
          ))}
        </Stepper>
        
        <Paper p="md" withBorder bg="rgba(255, 179, 0, 0.05)">
          <Stack align="center" spacing="sm">
            {currentControl && (
              <>
                <Title order={4} align="center">
                  {currentControl.name}
                </Title>
                
                <Text align="center">
                  {currentControl.type === 'button' ? (
                    <>Press and release the button for <strong>{currentControl.name}</strong> three times</>
                  ) : (
                    <>Move the <strong>{currentControl.name}</strong> left/right or up/down three times</>
                  )}
                </Text>
                
                <Box mt="md" style={{ width: '100%', maxWidth: '300px' }}>
                  <Progress value={(pressCount / 3) * 100} size="lg" color="amber" radius="xl" />
                  <Text align="center" mt="xs" fw={500} size="lg">
                    {pressCount} / 3
                  </Text>
                </Box>
                
                {detectedControl && (
                  <Badge color="amber" size="lg" mt="md">
                    Detected: {detectedControl.type === 'button' ? 'Button' : 'Axis'} #{detectedControl.index}
                  </Badge>
                )}
              </>
            )}
          </Stack>
        </Paper>
        
        <Box>
          <Text size="sm" c="dimmed" align="center" mb="md">
            {step + 1} of {controlsToMap.length} controls
          </Text>
          
          <Grid>
            <Grid.Col span={4}>
              <Button
                variant="outline"
                color="gray"
                fullWidth
                disabled={step === 0}
                onClick={goToPrevControl}
                leftIcon={<i className="fa-solid fa-arrow-left" />}
              >
                Back
              </Button>
            </Grid.Col>
            <Grid.Col span={4}>
              <Button
                variant="outline"
                color="amber"
                fullWidth
                onClick={skipControl}
                leftIcon={<i className="fa-solid fa-forward-step" />}
              >
                Skip
              </Button>
            </Grid.Col>
            <Grid.Col span={4}>
              <Button
                color="amber"
                fullWidth
                onClick={goToNextControl}
                rightIcon={<i className="fa-solid fa-arrow-right" />}
                disabled={pressCount < 3}
              >
                Next
              </Button>
            </Grid.Col>
          </Grid>
        </Box>
      </Stack>
    );
  };

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={
        <Group>
          <i className="fa-solid fa-gamepad" style={{ color: 'var(--mantine-color-amber-6)' }} />
          <Text fw={600}>Gamepad Mapping</Text>
        </Group>
      }
      centered
      size="lg"
      overlayProps={{
        color: 'rgba(0, 0, 0, 0.7)',
        opacity: 0.55,
        blur: 3,
      }}
    >
      {renderContent()}
    </Modal>
  );
};

export default GamepadMappingDialog;
