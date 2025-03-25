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
    { id: 'LEFT_ANALOG_STICK_X', name: 'Left Analog Stick (X - Left/Right)', type: 'axis' },
    { id: 'LEFT_ANALOG_STICK_Y', name: 'Left Analog Stick (Y - Up/Down)', type: 'axis' },
    { id: 'RIGHT_ANALOG_STICK_X', name: 'Right Analog Stick (X - Left/Right)', type: 'axis' },
    { id: 'RIGHT_ANALOG_STICK_Y', name: 'Right Analog Stick (Y - Up/Down)', type: 'axis' },
  ];
  
  // Generate profile name from gamepad ID
  const makeProfileName = (gamepad) => {
    if (!gamepad?.id) return 'Custom Gamepad Profile';
    
    // Extract vendor/product name if available
    const id = gamepad.id || '';
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
    if (!gamepad || !currentControlRef.current) {
      console.log("detectInput: gamepad or currentControl is missing", gamepad, currentControlRef.current);
      return;
    }
    
    const isAxisMapping = currentControlRef.current.type === 'axis';
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
    if (currentControlRef.current.type === 'axis' && type !== 'axis') return;
    
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
          [currentControlRef.current.id]: { type, index }
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
    setStep(prevStep => {
      const nextIndex = prevStep + 1;
      
      if (nextIndex >= controlsToMap.length) {
        setCurrentControl(null);
        console.log('Mapping complete, showing summary');
        return prevStep;
      }
      
      const nextControl = controlsToMap[nextIndex];
      if (!nextControl) {
        console.error(`No control found at index ${nextIndex}`);
        return prevStep;
      }
      
      setCurrentControl(nextControl);
      setDetectedControl(null);
      setPressCount(0);
      console.log(`Moving to control ${nextIndex}: ${nextControl.id}`);
      
      return nextIndex;
    });
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
    const currentGamepad = navigator.getGamepads()[gamepadIndex];
    if (!currentGamepad) {
      console.error('Cannot save profile - no gamepad detected');
      return;
    }

    const profileData = {
      id: currentGamepad.id,
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
        <Grid>
          <Grid.Col span={4}>
            <div style={{ 
              marginLeft: 'auto',
              marginRight: 'auto',
              paddingTop: '0rem',
              maxWidth: 'calc(17.5rem * var(--mantine-scale))',
              height: '250px',
              display: 'flex',
              flexDirection: 'column',
              width: '100%'
            }}>
              <Group gap="md" mb="md">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--mantine-color-gray-5)' }}>
                  <path d="M15 15m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"></path>
                  <path d="M18.5 18.5l2.5 2.5"></path>
                  <path d="M4 6h16"></path>
                  <path d="M4 12h4"></path>
                  <path d="M4 18h4"></path>
                </svg>
                <Text size="sm" c="dimmed">Controls to Map</Text>
              </Group>
              <Stack spacing={0} style={{ flex: 1, overflowY: 'auto' }}>
                {controlsToMap.map((control, index) => {
                  const isMapped = !!mapping[control.id];
                  const isSkipped = step > index && !isMapped;
                  const isCurrent = index === step;
                  
                  return (
                    <Group 
                      key={control.id} 
                      spacing="0" 
                      p={2}
                      pl={isCurrent ? 'md' : 'sm'}
                      style={{
                        cursor: 'pointer',
                        background: isCurrent ? 'var(--mantine-color-dark-6)' : 'transparent',
                        borderRadius: 'var(--mantine-radius-sm)',
                        transition: 'all 0.2s ease',
                        borderLeft: isCurrent ? '2px solid var(--mantine-color-amber-6)' : 'none',
                        marginBottom: '1px',
                        ':hover': {
                          background: 'var(--mantine-color-dark-5)',
                          paddingLeft: 'var(--mantine-spacing-md)'
                        }
                      }}
                      onClick={() => setStep(index)}
                    >
                        {isMapped ? (
                          <i className="fa-solid fa-circle-check" style={{color: 'var(--mantine-color-green-6)'}} />
                        ) : isSkipped ? (
                          <i className="fa-solid fa-circle-xmark" style={{color: 'var(--mantine-color-red-6)'}} />
                        ) : null}
                      <Text size="sm" style={{flex: 1}}>
                        {control.name}
                      </Text>
                    </Group>
                  );
                })}
              </Stack>
            </div>
          </Grid.Col>
          
          <Grid.Col span={8}>
            <Paper p="md" withBorder bg="rgba(255, 179, 0, 0.05)" style={{height: '100%'}}>
              <Stack align="center" spacing={8}>
            {currentControl && (
              <>
                <Title order={4} align="center">
                  {currentControl.name}
                </Title>
                
                <Text align="center">
                  {currentControl.type === 'button' ? (
                    <>Press and release the button for <strong>{currentControl.name}</strong> three times</>
                  ) : (
                    <>Move the <strong>{currentControl.name}</strong> {
                      currentControl.id.endsWith('_X') ? 'left/right' : 
                      currentControl.id.endsWith('_Y') ? 'up/down' : 
                      'in both directions'
                    } three times</>
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
            </Grid.Col>
          </Grid>

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
                disabled={step + 1 < controlsToMap.length && pressCount < 3}
              >
                {step + 1 >= controlsToMap.length ? 'Close' : 'Next'}
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
