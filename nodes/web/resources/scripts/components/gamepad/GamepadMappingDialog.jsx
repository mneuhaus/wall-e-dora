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
  Notification,
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
  const detectedControlRef = useRef(null);
  const [pressCount, setPressCount] = useState(0);
  const [isToastVisible, setIsToastVisible] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
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
      
      // Set first control to map
      setCurrentControl(controlsToMap[0]);
      
      // Set profile name
      setProfileName(makeProfileName(gamepad));
      
      // Enable mapping mode to pause WebSocket events
      if (gamepad) {
        gamepad.isMapping = true;
        console.log('Enabled mapping mode - pausing WebSocket event emission');
      }
      
      // Start polling for inputs
      startPolling();
      
      console.log('Dialog opened, set currentControl to:', controlsToMap[0]?.id);
    } else {
      // Clean up
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      
      // Disable mapping mode when dialog closes
      if (gamepad) {
        gamepad.isMapping = false;
        console.log('Disabled mapping mode - resuming WebSocket event emission');
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
    
    // Track axis changes that might be associated with button presses
    // (particularly useful for triggers which can have both button and axis inputs)
    const potentialAnalogAxes = [];
    
    // Initialize previous values if needed
    if (prevInputs.current.buttons.length === 0) {
      prevInputs.current = {
        buttons: Array(gamepad.buttons.length).fill(0),
        axes: Array(gamepad.axes.length).fill(0)
      };
    }
    
    // First check all axes for significant changes
    for (let i = 0; i < gamepad.axes.length; i++) {
      const axisValue = gamepad.axes[i];
      const prevValue = prevInputs.current.axes[i];
      const axisDelta = Math.abs(axisValue - prevValue);
      
      // For axis mapping, detect significant movements
      if (isAxisMapping && 
          (Math.abs(axisValue) > axisThreshold && Math.abs(prevValue) <= axisThreshold)) {
        console.log(`Axis ${i} moved: ${axisValue}`);
        recordInput('axis', i);
      }
      
      // For potential trigger detection - track axes that might be associated with a button
      // Record any axis with significant movement
      if (!isAxisMapping && axisDelta > 0.1) {
        potentialAnalogAxes.push({ 
          index: i, 
          value: axisValue, 
          delta: axisDelta 
        });
      }
      
      // Update previous value
      prevInputs.current.axes[i] = axisValue;
    }
    
    // Check all buttons
    for (let i = 0; i < gamepad.buttons.length; i++) {
      const buttonValue = gamepad.buttons[i].value;
      const prevValue = prevInputs.current.buttons[i];
      
      // For button mapping, detect new presses
      if (!isAxisMapping && buttonValue > buttonThreshold && prevValue <= buttonThreshold) {
        console.log(`Button ${i} pressed: ${buttonValue}`);
        
        // Special handling for controls that might be analog (triggers, etc.)
        // Check if any axes changed significantly along with this button press
        let analogAxisFound = false;
        
        // Check controls that are likely to be analog
        const isLikelyAnalog = (
          currentControlRef.current.id === 'LEFT_SHOULDER_BOTTOM' || 
          currentControlRef.current.id === 'RIGHT_SHOULDER_BOTTOM'
        );
        
        if (isLikelyAnalog && potentialAnalogAxes.length > 0) {
          // Sort by largest change first
          potentialAnalogAxes.sort((a, b) => b.delta - a.delta);
          
          // If we found an axis that changed significantly at the same time as the button press
          const bestMatch = potentialAnalogAxes[0];
          if (bestMatch && bestMatch.delta > 0.15) {
            console.log(`Found potential analog axis ${bestMatch.index} (delta: ${bestMatch.delta}) for button ${i}`);
            
            // Prefer the axis input for known analog controls like triggers
            recordInput('axis', bestMatch.index, true);
            analogAxisFound = true;
          }
        }
        
        // If no analog axis was found, fall back to button
        if (!analogAxisFound) {
          recordInput('button', i);
        }
      }
      
      // Update previous value
      prevInputs.current.buttons[i] = buttonValue;
    }
  };
  
  // Record a detected input
  const recordInput = (type, index, forceAnalog = false) => {
    console.log("recordInput called with", type, index, forceAnalog ? "(forced analog)" : "");
    
    // Ignore wrong types (unless we're forcing an axis for an analog control)
    if (currentControlRef.current.type === 'axis' && type !== 'axis') return;
    
    // Get current detected control from ref to avoid stale closures
    const currentDetection = detectedControlRef.current;
    
    // Reset if different from initial detection
    if (currentDetection && (currentDetection.type !== type || currentDetection.index !== index)) {
      console.log('Input changed - resetting counter');
      setPressCount(0);
      detectedControlRef.current = null;
      setDetectedControl(null);
      return;
    }
    
    // Get gamepad to check if this is an analog input (for buttons)
    const gamepad = navigator.getGamepads()[gamepadIndex];
    
    // Determine if this is an analog input
    let isAnalogInput = forceAnalog; // Always set to true if forceAnalog is true
    
    if (!isAnalogInput) {
      if (type === 'axis') {
        // All axes are considered analog
        isAnalogInput = true;
      } else if (type === 'button' && gamepad?.buttons[index]) {
        // Check if this button has non-binary values
        const buttonValue = gamepad.buttons[index].value;
        
        // Many gamepads have analog triggers even though they're buttons
        // We also check index values typical for triggers (6 and 7 in standard mapping)
        const isPotentialTrigger = index === 6 || index === 7 || 
                                  currentControlRef.current.id === 'LEFT_SHOULDER_BOTTOM' || 
                                  currentControlRef.current.id === 'RIGHT_SHOULDER_BOTTOM';
                                  
        // Buttons with values between 0.1 and 0.9 are likely analog
        isAnalogInput = (buttonValue > 0.1 && buttonValue < 0.9) || isPotentialTrigger;
        
        console.log(`Button ${index} value: ${buttonValue}, considered analog: ${isAnalogInput}`);
      }
    }
    
    // Record the input using both state and ref
    const inputData = { 
      type, 
      index,
      isAnalog: isAnalogInput 
    };
    
    // Add additional info for analog triggers detected via axis
    if (forceAnalog) {
      console.log(`Detected analog control (${currentControlRef.current.id}) mapped to ${type} ${index}`);
    }
    
    detectedControlRef.current = inputData;
    setDetectedControl(inputData);
    
    // Increment press count
    setPressCount(prev => {
      const newCount = prev + 1;
      
      // If we have 3 presses, move to next control
      if (newCount >= 3) {
        // Save mapping
        setMapping(prev => ({
          ...prev,
          [currentControlRef.current.id]: inputData
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
        return nextIndex;
      }
      
      const nextControl = controlsToMap[nextIndex];
      if (!nextControl) {
        console.error(`No control found at index ${nextIndex}`);
        return prevStep;
      }
      
      setCurrentControl(nextControl);
      setDetectedControl(null);
      detectedControlRef.current = null; // Reset ref too
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
  
  // Extract vendor and product IDs from gamepad ID
  const extractVendorProductIds = (gamepadId) => {
    const vendorMatch = gamepadId.match(/Vendor:\s*([0-9a-fA-F]+)/);
    const productMatch = gamepadId.match(/Product:\s*([0-9a-fA-F]+)/);
    
    const vendorId = vendorMatch && vendorMatch[1] ? vendorMatch[1].trim() : null;
    const productId = productMatch && productMatch[1] ? productMatch[1].trim() : null;
    
    return { vendorId, productId };
  };
  
  // Function to show toast notifications
  const showToast = (message) => {
    setToastMessage(message);
    setIsToastVisible(true);
    
    setTimeout(() => {
      setIsToastVisible(false);
    }, 3000);
  };

  // Save the profile
  const saveProfile = () => {
    const currentGamepad = navigator.getGamepads()[gamepadIndex];
    if (!currentGamepad) {
      console.error('Cannot save profile - no gamepad detected');
      return;
    }
    
    // Extract vendor and product IDs
    const { vendorId, productId } = extractVendorProductIds(currentGamepad.id);
    
    if (!vendorId || !productId) {
      console.warn('Could not extract vendor or product IDs:', currentGamepad.id);
      // Continue anyway, but log a warning
    }
    
    console.log(`Extracted vendorId: ${vendorId}, productId: ${productId}`);

    const profileData = {
      id: currentGamepad.id,
      vendorId: vendorId,
      productId: productId,
      name: profileName,
      mapping: mapping
    };
    
    console.log('Saving profile:', profileData);
    console.log('Profile stringified:', JSON.stringify(profileData));
    
    // Emit event to save profile
    node.emit('save_gamepad_profile', [profileData]);
    
    // Also add listener for profiles list updates
    const handleProfilesList = (event) => {
      if (event.id === 'gamepad_profiles_list') {
        console.log('Received profiles list after save:', event.value);
        node.off('gamepad_profiles_list', handleProfilesList);
      }
    };
    
    node.on('gamepad_profiles_list', handleProfilesList);
    
    // Show toast notification
    showToast(`Profile '${profileName}' saved successfully`);
    
    // Close the dialog immediately
    onClose();
  };
  
  // Render mapping UI or summary
  const renderContent = () => {
    // Mapping complete, show summary
    if (step >= controlsToMap.length) {
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
                                {mappedInput.isAnalog && ' (Analog)'}
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
              gap: 'var(--mantine-spacing-xs)',
              flexDirection: 'column',
              width: '100%'
            }}>
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
    <>
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
      
      {/* Toast notification */}
      {isToastVisible && (
        <Notification
          color="green"
          title="Success"
          onClose={() => setIsToastVisible(false)}
          withCloseButton
          withBorder={true}
          pos="fixed"
          style={{ 
            top: '16px', 
            right: '16px', 
            zIndex: 1000,
            animation: 'fadeIn 0.3s'
          }}
          sx={{
            '@keyframes fadeIn': {
              from: { opacity: 0 },
              to: { opacity: 1 }
            }
          }}
        >
          {toastMessage}
        </Notification>
      )}
    </>
  );
};

export default GamepadMappingDialog;
