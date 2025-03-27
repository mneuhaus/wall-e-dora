/**
 * ServoDebugView Component
 * 
 * A comprehensive interface for debugging and configuring a single servo.
 * Provides intuitive controls for position, speed, calibration, and advanced configuration.
 * 
 * Features:
 * - Visual circular position control
 * - Real-time status monitoring
 * - Servo calibration tools
 * - Gamepad control mapping
 * - Configuration management
 * 
 * @component
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import node from '../Node';
import gamepads from '../Gamepads';
import { CircularSliderWithChildren } from 'react-circular-slider-svg';
import { keyframes, css } from '@emotion/css';

// Mantine imports
import { 
  Container, 
  Paper, 
  Title, 
  Text, 
  Group, 
  Stack, 
  Button, 
  TextInput, 
  NumberInput,
  Select,
  Slider, 
  Badge, 
  ActionIcon,
  Divider,
  Grid,
  Box,
  Modal,
  Switch,
  Radio,
  Notification,
  Table,
  rem,
  Tooltip
} from '@mantine/core';

// We'll use a direct style object for the animation instead of CSS-in-JS
const getFlashStyle = () => ({
  animation: 'servo-flash 500ms ease-out',
  position: 'relative',
  zIndex: 10
});

// Add the keyframes to the document head
const useFlashAnimation = () => {
  useEffect(() => {
    // Only add the keyframes if they don't already exist
    if (!document.getElementById('servo-flash-keyframes')) {
      const style = document.createElement('style');
      style.id = 'servo-flash-keyframes';
      style.innerHTML = `
        @keyframes servo-flash {
          0% { background-color: rgba(255, 179, 0, 0.5); }
          50% { background-color: rgba(255, 179, 0, 0.3); }
          100% { background-color: rgba(255, 179, 0, 0); }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);
};

const ServoDebugView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [servo, setServo] = useState(null);
  
  // Initialize the flash animation
  useFlashAnimation();
  const [position, setPosition] = useState(0);
  const [displayPosition, setDisplayPosition] = useState(0); // For UI display (0-300 degrees)
  const [speed, setSpeed] = useState(null); // Start with null so we know when it's initialized from server
  const [sliderReady, setSliderReady] = useState(false); // Track if slider should be rendered
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(1023);
  const [aliasInput, setAliasInput] = useState('');
  const [attachIndex, setAttachIndex] = useState("");
  const [controlType, setControlType] = useState(""); // 'button' or 'axis'
  const [controlMode, setControlMode] = useState(""); // 'toggle'/'momentary' for buttons, 'absolute'/'relative' for axes
  const [invertControl, setInvertControl] = useState(false);
  const [multiplier, setMultiplier] = useState(1);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [openedModal, setOpenedModal] = useState(null); // For tracking which modal is open
  const [isToastVisible, setIsToastVisible] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState('success');
  const [isControlActive, setIsControlActive] = useState(false); // Track if attached control is active
  const controlFlashTimeout = useRef(null);
  const positionUpdateTimeout = useRef(null);
  
  // Monitor isControlActive state changes
  useEffect(() => {
    console.log(`isControlActive changed to: ${isControlActive}`);
  }, [isControlActive]);

  // Function to show toast notifications
  const showToast = (message, type = 'success') => {
    setToastMessage(message);
    setToastType(type);
    setIsToastVisible(true);
    
    setTimeout(() => {
      setIsToastVisible(false);
    }, 3000);
  };
  
  // Map BeerCSS toast types to Mantine colors
  const getToastColor = (type) => {
    switch (type) {
      case 'success': return 'green';
      case 'error': return 'red';
      case 'info': return 'blue';
      default: return 'amber';
    }
  };
  
  // Helper function to map servo position to UI angle (0-300 degrees)
  const mapServoToUI = useCallback((servoPos, servoMin, servoMax) => {
    // Validate inputs to prevent NaN
    if (servoPos === null || servoPos === undefined || typeof servoPos !== 'number' || isNaN(servoPos)) {
      return 0;
    }
    
    if (servoMin === null || servoMin === undefined || typeof servoMin !== 'number' || isNaN(servoMin)) {
      servoMin = 0; // Default min
    }
    
    if (servoMax === null || servoMax === undefined || typeof servoMax !== 'number' || isNaN(servoMax)) {
      servoMax = 1023; // Default max
    }
    
    // Ensure min and max are valid
    if (servoMin < 0) servoMin = 0;
    if (servoMax > 1023) servoMax = 1023;
    if (servoMax <= servoMin) {
      servoMin = 0;
      servoMax = 1023;
    }
    
    // Make sure servo position is within bounds
    if (servoPos < servoMin) servoPos = servoMin;
    if (servoPos > servoMax) servoPos = servoMax;
    
    // Map servo position (min-max) to UI angle (0-300 degrees)
    const range = servoMax - servoMin;
    if (range === 0) return 0; // Avoid division by zero
    
    return Math.round(300 * ((servoPos - servoMin) / range));
  }, []);
  
  // Helper function to map UI angle to servo position
  const mapUIToServo = useCallback((uiPos, servoMin, servoMax) => {
    // Validate inputs to prevent NaN
    if (uiPos === null || uiPos === undefined || typeof uiPos !== 'number' || isNaN(uiPos)) {
      return 0;
    }
    
    // Get current servo range, default to 0-1023 if invalid
    if (servoMin === null || servoMin === undefined || typeof servoMin !== 'number' || isNaN(servoMin)) {
      servoMin = 0;
    }
    
    if (servoMax === null || servoMax === undefined || typeof servoMax !== 'number' || isNaN(servoMax)) {
      servoMax = 1023;
    }
    
    // Ensure min and max are valid and min < max
    if (servoMin < 0) servoMin = 0;
    if (servoMax > 1023) servoMax = 1023;
    if (servoMax <= servoMin) {
      servoMin = 0;
      servoMax = 1023;
    }
    
    // Map UI angle (0-300 degrees) to servo position (min-max)
    // 300 degrees = full range from min to max
    const range = servoMax - servoMin;
    return Math.round(servoMin + (uiPos / 300) * range);
  }, []);

  // Force slider to re-render when displayPosition changes
  useEffect(() => {
    if (displayPosition !== 0 && !sliderReady) {
      setTimeout(() => setSliderReady(true), 50);
    }
  }, [displayPosition, sliderReady]);
  
  // Initialize modal data when opened
  useEffect(() => {
    // If gamepad modal is opened, initialize with existing config if available
    if (openedModal === 'gamepad' && servo?.gamepad_config) {
      const config = servo.gamepad_config;
      
      // Set values from existing config
      setAttachIndex(config.control || '');
      setControlType(config.type || '');
      setControlMode(config.mode || '');
      setInvertControl(config.invert || false);
      setMultiplier(config.multiplier || 1);
    }
  }, [openedModal]); // Remove servo dependency to prevent re-initialization when servo data updates

  // Super simple gamepad control listener
  useEffect(() => {
    if (!servo?.attached_control) return;
    
    const controlName = servo.attached_control;
    console.log(`Setting up simple listener for GAMEPAD_${controlName}`);
    
    // Create a super simple, direct event handler
    function handleGamepadButtonPress(event) {
      // Log every event for debugging
      console.log(`GAMEPAD EVENT: ${controlName}`, event);
      
      // Just flash for any event
      setIsControlActive(true);
      
      // Set a timeout to turn it off
      setTimeout(() => {
        setIsControlActive(false);
      }, 1000);
    }
    
    // Add direct event listener
    window.addEventListener(`GAMEPAD_${controlName}`, handleGamepadButtonPress);
    
    // Also listen via node for redundancy
    const nodeListener = node.on(`GAMEPAD_${controlName}`, handleGamepadButtonPress);
    
    // Test the flashing right away (for debugging)
    console.log("Testing control flash animation...");
    setIsControlActive(true);
    setTimeout(() => setIsControlActive(false), 1000);
    
    // Clean up
    return () => {
      window.removeEventListener(`GAMEPAD_${controlName}`, handleGamepadButtonPress);
      if (nodeListener) nodeListener();
    };
  }, [servo?.attached_control]);
  
  useEffect(() => {
    // Function to process servo data (reused for both event types)
    const processServoData = (servoInfo) => {
      if (!servoInfo) return;
      
      // Create a safe copy of the servo data that preserves gamepad_config when modal is open
      const updatedServoData = { ...servoInfo };
      
      // If the gamepad modal is open, preserve the current gamepad config
      // to prevent websocket updates from overwriting the unsaved changes
      if (openedModal === 'gamepad' && servo?.gamepad_config) {
        updatedServoData.gamepad_config = servo.gamepad_config;
        updatedServoData.attached_control = servo.attached_control;
      }
      
      // Update the servo state with our protected data
      setServo(updatedServoData);
      
      // Get min/max pulse values from servo data or use defaults
      let servoMinPulse = 0;
      let servoMaxPulse = 1023;
      
      if (servoInfo.min_pulse !== undefined && servoInfo.min_pulse !== null && 
          !isNaN(servoInfo.min_pulse) && servoInfo.min_pulse >= 0) {
        servoMinPulse = Number(servoInfo.min_pulse);
      }
      
      if (servoInfo.max_pulse !== undefined && servoInfo.max_pulse !== null && 
          !isNaN(servoInfo.max_pulse) && servoInfo.max_pulse <= 1023) {
        servoMaxPulse = Number(servoInfo.max_pulse);
      }
      
      // Ensure min < max
      if (servoMaxPulse <= servoMinPulse) {
        servoMinPulse = 0;
        servoMaxPulse = 1023;
      }
      
      // Update state with the min/max values
      setMin(servoMinPulse);
      setMax(servoMaxPulse);
      
      // Get current servo position with validation
      let servoPosition = 0;
      if (servoInfo.position !== undefined && servoInfo.position !== null && !isNaN(servoInfo.position)) {
        servoPosition = Number(servoInfo.position);
      }
      
      // Set raw position value
      setPosition(servoPosition);
      
      // Map servo position to UI range (0-300 degrees) using actual min/max
      const uiPosition = mapServoToUI(servoPosition, servoMinPulse, servoMaxPulse);
      
      // Validate before setting
      if (typeof uiPosition === 'number' && !isNaN(uiPosition)) {
        setDisplayPosition(uiPosition);
        // Ensure slider becomes ready after position is set
        if (!sliderReady) {
          setTimeout(() => setSliderReady(true), 50);
        }
      } else {
        setDisplayPosition(0); // Default to 0 if invalid
        // Even with invalid position, we should still render the slider
        if (!sliderReady) {
          setTimeout(() => setSliderReady(true), 50);
        }
      }
      
      // Set speed - IMPORTANT: This needs to work on page load
      if (servoInfo.speed !== undefined && servoInfo.speed !== null) {
        setSpeed(Number(servoInfo.speed));
      } else {
        setSpeed(1000); // Default speed
      }
      
      // Update alias input if it's empty and the servo has an alias
      // and alias modal is not open to prevent overwriting unsaved changes
      if (aliasInput === '' && servoInfo.alias && openedModal !== 'alias') {
        setAliasInput(servoInfo.alias);
      }
    };
    
    // Listen for servo updates
    const unsubscribe = node.on('servo_status', (event) => {
      const servoData = event.value || [];
      // Check if we're getting a single servo or an array
      const servoInfo = Array.isArray(servoData) ? 
                        servoData.find(s => s.id === parseInt(id)) : 
                        (servoData.id === parseInt(id) ? servoData : null);
      
      if (servoInfo) {
        processServoData(servoInfo);
      }
    });
    
    // Listen for servos_list for full servo info
    const listUnsubscribe = node.on('servos_list', (event) => {
      const servosList = event.value || [];
      const currentServo = servosList.find(s => s.id === parseInt(id));
      if (currentServo) {
        // Use the same processor function for consistency
        processServoData(currentServo);
      }
    });
    
    // No need to manually request scan, it happens automatically on timer
    
    return () => {
      unsubscribe();
      listUnsubscribe();
    };
  }, [id, mapServoToUI, aliasInput]);
  
  const handlePositionChange = (newPosition) => {
    // Validate that newPosition is a valid number
    if (newPosition === null || newPosition === undefined || 
        typeof newPosition !== 'number' || isNaN(newPosition)) {
      return;
    }
    
    // Ensure slider is marked as ready
    if (!sliderReady) {
      setSliderReady(true);
    }
    
    // Update display position immediately for responsive UI
    setDisplayPosition(newPosition);
    
    // Validate min and max before passing to mapUIToServo
    let servoMin = min;
    let servoMax = max;
    
    if (servoMin === null || servoMin === undefined || typeof servoMin !== 'number' || isNaN(servoMin)) {
      servoMin = 0; // Default min
    }
    
    if (servoMax === null || servoMax === undefined || typeof servoMax !== 'number' || isNaN(servoMax)) {
      servoMax = 1023; // Default max
    }
    
    // Ensure min/max are valid
    if (servoMin < 0) servoMin = 0;
    if (servoMax > 1023) servoMax = 1023;
    if (servoMax <= servoMin) {
      servoMin = 0;
      servoMax = 1023;
    }
    
    // Map UI range (0-300) to servo range (min-max)
    const servoPosition = mapUIToServo(newPosition, servoMin, servoMax);
    
    // Validate servoPosition before setting it
    if (servoPosition === null || servoPosition === undefined || 
        typeof servoPosition !== 'number' || isNaN(servoPosition)) {
      return;
    }
    
    setPosition(servoPosition);
    
    // Debounce servo commands
    clearTimeout(positionUpdateTimeout.current);
    positionUpdateTimeout.current = setTimeout(() => {
      // New format for move_servo command
      node.emit('move_servo', [{
        id: parseInt(id),
        position: servoPosition
      }]);
    }, 50);
  };
  
  const handleSpeedChange = (newSpeed) => {
    setSpeed(newSpeed);
    // Don't update the server on every change, only when done dragging
  };
  
  const handleSpeedChangeComplete = (newSpeed) => {
    // Update servo setting format only when slider interaction is complete
    node.emit('update_servo_setting', [{
      id: parseInt(id),
      property: "speed",
      value: newSpeed
    }]);
    showToast(`Speed set to ${newSpeed}`);
  };
  
  const handleWiggle = () => {
    setIsTesting(true);
    // Updated wiggle_servo command format
    node.emit('wiggle_servo', [{
      id: parseInt(id)
    }]);
    showToast('Testing servo motion...');
    
    // Auto-disable testing mode after 3 seconds
    setTimeout(() => {
      setIsTesting(false);
    }, 3000);
  };
  
  const handleCalibrate = () => {
    // Ask for confirmation before calibrating
    if (!window.confirm('Are you sure you want to calibrate this servo? This will find the physical limits of the servo\'s range of motion.')) {
      return; // User canceled
    }
    
    setIsCalibrating(true);
    // Updated calibrate_servo command format
    node.emit('calibrate_servo', [{
      id: parseInt(id)
    }]);
    showToast('Calibrating servo range...', 'info');
    
    // Auto-disable calibration mode after 3 seconds
    setTimeout(() => {
      setIsCalibrating(false);
      showToast('Calibration complete!');
    }, 3000);
  };
  
  // handleChangeId function removed as it's rarely needed
  
  const handleSetAlias = () => {
    if (aliasInput.trim() === '') return;
    
    const servoId = parseInt(id);
    const trimmedAlias = aliasInput.trim();
    
    // Update local state immediately to prevent UI flicker
    const updatedServo = { ...servo };
    updatedServo.alias = trimmedAlias;
    setServo(updatedServo);
    
    // Use the servo-specific setting update endpoint
    node.emit('update_servo_setting', [{
      id: servoId,
      property: "alias",
      value: trimmedAlias
    }]);
    
    showToast(`Alias set to "${trimmedAlias}"`);
  };
  
  const handleAttachServo = () => {
    if (!attachIndex || !controlType || !controlMode) return;
    
    // Build gamepad configuration object with all needed parameters
    const gamepadConfig = {
      control: attachIndex,
      type: controlType, // 'button' or 'axis'
      mode: controlMode, // 'toggle'/'momentary' for buttons, 'absolute'/'relative' for axes
      invert: invertControl,
      multiplier: multiplier
    };
    
    
    // Also update the local servo state immediately to prevent UI flicker
    // and ensure UI consistency even if websocket updates are delayed
    const updatedServo = { ...servo };
    updatedServo.gamepad_config = gamepadConfig;
    updatedServo.attached_control = attachIndex;
    setServo(updatedServo);
    
    // Update the gamepad config (this will be merged with any existing data)
    // Send both updates in quick succession
    node.emit('update_servo_setting', [{
      id: parseInt(id),
      property: "gamepad_config",
      value: gamepadConfig
    }]);
    
    // Also set the attached_control for backward compatibility
    node.emit('update_servo_setting', [{
      id: parseInt(id),
      property: "attached_control",
      value: attachIndex
    }]);
    
    showToast(`Attached to gamepad control: ${attachIndex} (${controlMode} mode)`);
  };
  
  const handleResetServo = () => {
    if (window.confirm('Are you sure you want to reset this servo to factory defaults? This will remove all calibration settings and aliases.')) {
      // Reset servo settings to defaults
      const servoId = parseInt(id);
      const defaultSettings = {
        min_pulse: 0,
        max_pulse: 1023,
        speed: 1000,
        calibrated: false,
        alias: "",
        invert: false,
        attached_control: "",
        gamepad_config: {}
      };
      
      // Update each setting to default
      for (const [prop, value] of Object.entries(defaultSettings)) {
        node.emit('update_servo_setting', [{
          id: servoId,
          property: prop,
          value: value
        }]);
      }
      
      showToast('Servo reset to factory defaults', 'info');
    }
  };
  
  const loadingView = (
    <Container size="lg" py="md">
      <Paper p="md" radius="md" withBorder={true}>
        <Group justify="space-between" mb="md">
          <Group>
            <ActionIcon component={Link} to="/" variant="subtle" color="amber" radius="xl">
              <i className="fa-solid fa-arrow-left"></i>
            </ActionIcon>
            <Title order={5}>Loading Servo Data...</Title>
          </Group>
        </Group>
        <Stack align="center" p="xl">
          <Box 
            sx={{
              width: rem(48),
              height: rem(48),
              border: '4px solid rgba(255, 255, 255, 0.2)',
              borderTop: '4px solid var(--mantine-color-amber-6)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              '@keyframes spin': {
                '0%': { transform: 'rotate(0deg)' },
                '100%': { transform: 'rotate(360deg)' }
              }
            }}
          ></Box>
          <Text c="dimmed">Connecting to Servo {id}</Text>
        </Stack>
      </Paper>
    </Container>
  );
  
  if (!servo) {
    return loadingView;
  }
  
  // Create custom servo status object to handle special rendering for attached control
  const servoStatus = {
    'Voltage': servo.voltage ? `${servo.voltage.toFixed(1)}V` : 'N/A',
    'Min Pulse': servo.min_pulse !== undefined ? servo.min_pulse : 'Not calibrated',
    'Max Pulse': servo.max_pulse !== undefined ? servo.max_pulse : 'Not calibrated'
  };
  
  return (
    <Container size="lg" py="md">
      {/* Toast notification */}
      {isToastVisible && (
        <Notification
          color={getToastColor(toastType)}
          title={toastType.charAt(0).toUpperCase() + toastType.slice(1)}
          onClose={() => setIsToastVisible(false)}
          withCloseButton
          withBorder={true}
          pos="fixed"
          style={{ 
            top: rem(16), 
            right: rem(16), 
            zIndex: 1000,
            animation: 'fadeIn 0.3s'
          }}
          sx={{
            '@keyframes fadeIn': {
              from: { opacity: 0 },
              to: { opacity: 1 }
            }
          }}
          w={rem(300)}
        >
          {toastMessage}
        </Notification>
      )}
      
      <Paper radius="md" withBorder={true} p={0}>
        {/* Header Section */}
        <Box py="xs" px="md" bg="rgba(255, 215, 0, 0.05)" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', height: '45px' }}>
          <Group justify="space-between">
            <Group>
              <ActionIcon component={Link} to="/" variant="subtle" color="amber" radius="xl">
                <i className="fa-solid fa-arrow-left"></i>
              </ActionIcon>
              <Title order={5}>
                {servo.alias ? `${servo.alias} (#${id})` : `Servo #${id}`}
              </Title>
            </Group>
            <Group spacing="xs">
              <Tooltip label="Test Servo">
                <ActionIcon 
                  color="amber" 
                  variant={isTesting ? "filled" : "subtle"}
                  radius="xl" 
                  onClick={handleWiggle}
                  disabled={isTesting}
                >
                  <i className="fa-solid fa-arrows-left-right"></i>
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Calibrate Servo">
                <ActionIcon 
                  color="amber" 
                  variant={isCalibrating ? "filled" : "subtle"}
                  radius="xl" 
                  onClick={handleCalibrate}
                  disabled={isCalibrating}
                >
                  <i className="fa-solid fa-ruler"></i>
                </ActionIcon>
              </Tooltip>
              <Divider orientation="vertical" mx={2} />
              <Tooltip label="Edit Alias">
                <ActionIcon 
                  color="amber" 
                  variant="subtle" 
                  radius="xl" 
                  onClick={() => setOpenedModal('alias')}
                >
                  <i className="fa-solid fa-tag"></i>
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Gamepad Mapping">
                <ActionIcon 
                  color="amber" 
                  variant="subtle" 
                  radius="xl" 
                  onClick={() => setOpenedModal('gamepad')}
                >
                  <i className="fa-solid fa-gamepad"></i>
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Advanced Settings">
                <ActionIcon 
                  color="amber" 
                  variant="subtle" 
                  radius="xl" 
                  onClick={() => setOpenedModal('advanced')}
                >
                  <i className="fa-solid fa-cog"></i>
                </ActionIcon>
              </Tooltip>
            </Group>
          </Group>
        </Box>
        
        <Box p={0}>
          <Grid gutter={5} style={{ margin: 0 }}>
            {/* Control Section */}
            <Grid.Col span={6} p={5}>
              <Stack spacing={2} align="center">
                <Box sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  position: 'relative'
                }}>
                  {/* Render slider when it's ready */}
                  {sliderReady ? (
                    <CircularSliderWithChildren
                      size={234} 
                      minValue={0}
                      maxValue={300}
                      startAngle={0}
                      endAngle={300}
                      handleSize={14} 
                      handle1={{
                        value: displayPosition,
                        onChange: handlePositionChange
                      }}
                      arcColor="#FFB300"
                      arcBackgroundColor="rgba(255, 179, 0, 0.15)"
                      coerceToInt={true}
                      handleColor="#FFB300"
                      trackColor="rgba(255, 179, 0, 0.05)"
                    >
                      <div 
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          textAlign: 'center',
                          width: '100%',
                          height: '100%',
                          marginTop: '2px'
                        }}
                      >
                        <Text size="xl" fw={700} c="amber" lh={1}>
                          {typeof displayPosition === 'number' && !isNaN(displayPosition) ? 
                            `${displayPosition}°` : 
                            '0°'
                          }
                        </Text>
                        <Text size="sm" c="dimmed" lh={1} mb={3}>angle</Text>
                        <Badge color="amber" variant="light" size="xs" radius="sm" px={5} py={1} 
                          sx={{ 
                            boxShadow: "0 0 4px rgba(255, 179, 0, 0.4)",
                            background: "rgba(255, 179, 0, 0.1)",
                            border: "1px solid rgba(255, 179, 0, 0.3)"
                          }}
                        >
                          {position || '0'}
                        </Badge>
                        <Text size="2xs" c="dimmed" lh={1} mt={2}>pulse</Text>
                      </div>
                    </CircularSliderWithChildren>
                  ) : (
                    <Box 
                      style={{ 
                        width: 234, 
                        height: 234, 
                        display: 'flex', 
                        flexDirection: 'column',
                        alignItems: 'center', 
                        justifyContent: 'center',
                        border: '3px solid rgba(255, 179, 0, 0.3)',
                        borderRadius: '50%',
                        color: 'var(--mantine-color-dimmed)',
                        background: 'rgba(255, 179, 0, 0.05)',
                        boxShadow: '0 0 15px rgba(255, 179, 0, 0.2)'
                      }}
                    >
                      <Box 
                        sx={{
                          width: rem(24),
                          height: rem(24),
                          border: '3px solid rgba(255, 255, 255, 0.1)',
                          borderTop: '3px solid var(--mantine-color-amber-5)',
                          borderRadius: '50%',
                          animation: 'spin 1s linear infinite',
                          marginBottom: rem(3)
                        }}
                      ></Box>
                      <Text size="xs" c="dimmed" lh={1}>Loading...</Text>
                    </Box>
                  )}
                </Box>
              </Stack>
            </Grid.Col>
          
            {/* Info Section */}
            <Grid.Col span={6} p={5}>
              {/* Speed slider section */}
              <Box w="100%" style={{ marginBottom: '15px', marginTop: '8px', paddingLeft: '10px', paddingRight: '10px' }}>
                <Group justify="space-between" mb={1}>
                  <Text fw={500} style={{ fontSize: '0.75rem' }}>Speed</Text>
                  <Badge color="amber" variant="filled" size="xs" 
                    style={{
                      boxShadow: "0 0 4px rgba(255, 179, 0, 0.4)",
                      border: "1px solid rgba(255, 179, 0, 0.6)"
                    }}
                  >
                    {speed !== null ? speed : 'Loading...'}
                  </Badge>
                </Group>
                {speed !== null ? (
                  <Slider
                    min={50}
                    max={2000}
                    step={50}
                    value={speed}
                    onChange={handleSpeedChange}
                    onChangeEnd={handleSpeedChangeComplete}
                    color="amber"
                    labelAlwaysOn={false}
                    size="xs"
                    style={{ marginBottom: 2 }}
                  />
                ) : (
                  <div style={{ height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--mantine-color-dimmed)' }}>Loading...</span>
                  </div>
                )}
                <Text c="dimmed" style={{ marginTop: 0, fontSize: '0.65rem' }}>Lower = faster</Text>
              </Box>
              <Box style={{ overflowY: 'auto', padding: '10px' }}>
                <Table striped highlightOnHover withTableBorder>
                  <Table.Tbody>
                    {/* Custom Attached Control row with animation */}
                    <Table.Tr 
                      style={isControlActive ? {
                        backgroundColor: "rgba(255, 179, 0, 0.3)", 
                        transition: "background-color 0.5s",
                        position: "relative",
                        zIndex: 10
                      } : {}}
                    >
                      <Table.Td style={{ fontWeight: 500, color: 'var(--mantine-color-dimmed)', fontSize: '0.75rem', padding: '1px 6px' }}>
                        Attached Control
                      </Table.Td>
                      <Table.Td style={{ 
                        color: isControlActive ? 'var(--mantine-color-amber-9)' : 'var(--mantine-color-amber-filled)', 
                        textAlign: 'right', 
                        fontSize: '0.75rem', 
                        padding: '1px 6px',
                        fontWeight: isControlActive ? 600 : 400,
                        transition: 'color 0.2s, font-weight 0.2s'
                      }}>
                        {servo.attached_control ? (
                          <Group justify="right" spacing="xs" wrap="nowrap">
                            <div
                              style={{
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                backgroundColor: isControlActive ? '#4CAF50' : 'rgba(255, 179, 0, 0.5)',
                                display: 'inline-block',
                                marginRight: '4px',
                                boxShadow: isControlActive ? '0 0 5px #4CAF50' : 'none',
                                transition: 'background-color 0.2s, box-shadow 0.2s'
                              }}
                            />
                            {servo.attached_control}
                            {servo.gamepad_config?.mode && (
                              <Text span size="xs" c="dimmed">({servo.gamepad_config.mode})</Text>
                            )}
                          </Group>
                        ) : (
                          'None'
                        )}
                      </Table.Td>
                    </Table.Tr>
                    
                    {/* Standard rows for other properties */}
                    {Object.entries(servoStatus).map(([key, value]) => (
                      <Table.Tr key={key}>
                        <Table.Td style={{ fontWeight: 500, color: 'var(--mantine-color-dimmed)', fontSize: '0.75rem', padding: '1px 6px' }}>{key}</Table.Td>
                        <Table.Td style={{ color: 'var(--mantine-color-amber-filled)', textAlign: 'right', fontSize: '0.75rem', padding: '1px 6px' }}>
                          {key === 'Voltage' && servo.voltage ? (
                            <Group justify="right" spacing="xs" wrap="nowrap">
                              <div
                                style={{
                                  width: '6px',
                                  height: '6px',
                                  borderRadius: '50%',
                                  backgroundColor: servo.voltage >= 6.0 ? '#4CAF50' : (servo.voltage >= 5.0 ? '#FFC107' : '#F44336'),
                                  display: 'inline-block',
                                  marginRight: '2px'
                                }}
                              />
                              {value}
                            </Group>
                          ) : (
                            value
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
                
                {servo.properties && Object.keys(servo.properties).length > 0 && (
                  <>
                    <Text fw={500} c="amber" mt="xs" mb="xs" size="xs">Advanced Properties</Text>
                    <Table size="xs" striped highlightOnHover withTableBorder>
                      <Table.Tbody>
                        {Object.entries(servo.properties).map(([key, value]) => (
                          <Table.Tr key={key}>
                            <Table.Td style={{ fontWeight: 500, color: 'var(--mantine-color-dimmed)', fontSize: '0.65rem', padding: '1px 4px' }}>{key}</Table.Td>
                            <Table.Td style={{ textAlign: 'right', fontSize: '0.65rem', padding: '1px 4px' }}>{value}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </>
                )}
              </Box>
            </Grid.Col>
          </Grid>
        </Box>
      </Paper>
      
      {/* Modals */}
      {/* Alias Modal */}
      <Modal
        opened={openedModal === 'alias'}
        onClose={() => setOpenedModal(null)}
        title={<Text fw={600} c="amber">Edit Servo Alias</Text>}
        size="md"
        centered
        overlayProps={{
          color: 'rgb(0, 0, 0)',
          opacity: 0.55,
          blur: 3,
        }}
      >
        <Stack spacing="md">
          <TextInput
            label="Servo Alias"
            placeholder="Friendly name for this servo"
            value={aliasInput}
            onChange={(e) => setAliasInput(e.target.value)}
            maxLength={20}
          />
          <Text size="sm" c="dimmed">
            Give your servo a meaningful name to easily identify it in the servo list.
          </Text>
          <Group position="right" mt="md">
            <Button 
              variant="outline" 
              color="gray" 
              onClick={() => setOpenedModal(null)}
            >
              Cancel
            </Button>
            <Button 
              variant="filled" 
              color="amber" 
              onClick={() => {
                handleSetAlias();
                setOpenedModal(null);
              }}
              disabled={!aliasInput.trim()}
            >
              Save Alias
            </Button>
          </Group>
        </Stack>
      </Modal>
      
      {/* Gamepad Mapping Modal */}
      <Modal
        opened={openedModal === 'gamepad'}
        onClose={() => {
          // Only reset if we're not currently attached or don't have config
          if (!servo?.gamepad_config) {
            setAttachIndex('');
            setControlType('');
            setControlMode('');
            setInvertControl(false);
            setMultiplier(1);
          }
          setOpenedModal(null);
        }}
        title={<Text fw={600} c="amber">Gamepad Control Mapping</Text>}
        size="lg"
        centered
        overlayProps={{
          color: 'rgb(0, 0, 0)',
          opacity: 0.55,
          blur: 3,
        }}
      >
        <Stack spacing="md">
          <Text size="sm">Map this servo to a gamepad control for remote operation</Text>
          
          {/* Control Selection */}
          <Select
            label="Gamepad Control"
            placeholder="Choose a control"
            value={attachIndex}
            onChange={(value) => {
              setAttachIndex(value);
              
              // Determine if it's a button or axis based on the selection
              if (value && value.includes('STICK')) {
                setControlType('axis');
                // Default to absolute mode for axes
                if (!controlMode || controlMode === 'toggle' || controlMode === 'momentary') {
                  setControlMode('absolute');
                }
              } else if (value) {
                setControlType('button');
                // Default to toggle mode for buttons
                if (!controlMode || controlMode === 'absolute' || controlMode === 'relative') {
                  setControlMode('toggle');
                }
              }
            }}
            data={[
              { group: 'Buttons', items: [
                { value: 'FACE_1', label: 'FACE_1 (A/Cross)' },
                { value: 'FACE_2', label: 'FACE_2 (B/Circle)' },
                { value: 'FACE_3', label: 'FACE_3 (X/Square)' },
                { value: 'FACE_4', label: 'FACE_4 (Y/Triangle)' },
                { value: 'LEFT_SHOULDER', label: 'LEFT_SHOULDER (LB)' },
                { value: 'RIGHT_SHOULDER', label: 'RIGHT_SHOULDER (RB)' },
                { value: 'LEFT_SHOULDER_BOTTOM', label: 'LEFT_SHOULDER_BOTTOM (LT)' },
                { value: 'RIGHT_SHOULDER_BOTTOM', label: 'RIGHT_SHOULDER_BOTTOM (RT)' },
                { value: 'SELECT', label: 'SELECT (Back/Share)' },
                { value: 'START', label: 'START (Start/Options)' },
                { value: 'LEFT_ANALOG_BUTTON', label: 'LEFT_ANALOG_BUTTON (L3)' },
                { value: 'RIGHT_ANALOG_BUTTON', label: 'RIGHT_ANALOG_BUTTON (R3)' },
                { value: 'DPAD_UP', label: 'DPAD_UP' },
                { value: 'DPAD_DOWN', label: 'DPAD_DOWN' },
                { value: 'DPAD_LEFT', label: 'DPAD_LEFT' },
                { value: 'DPAD_RIGHT', label: 'DPAD_RIGHT' },
                { value: 'HOME', label: 'HOME (Guide/PS)' },
              ]},
              { group: 'Axes', items: [
                { value: 'LEFT_ANALOG_STICK_X', label: 'LEFT_ANALOG_STICK_X' },
                { value: 'LEFT_ANALOG_STICK_Y', label: 'LEFT_ANALOG_STICK_Y' },
                { value: 'RIGHT_ANALOG_STICK_X', label: 'RIGHT_ANALOG_STICK_X' },
                { value: 'RIGHT_ANALOG_STICK_Y', label: 'RIGHT_ANALOG_STICK_Y' },
              ]}
            ]}
          />
          
          {/* Conditional UI based on control type */}
          {attachIndex && (
            <>
              <Divider label="Control Configuration" labelPosition="center" />
              
              {/* Common options */}
              <Grid>
                <Grid.Col span={controlType === 'axis' ? 6 : 12}>
                  <Box 
                    py="xs"
                    px="md"
                    sx={{ 
                      border: '1px solid rgba(255, 179, 0, 0.2)',
                      borderRadius: 'var(--mantine-radius-md)',
                      background: 'rgba(255, 179, 0, 0.05)'
                    }}
                  >
                    <Group position="apart" mb="sm">
                      <Text fw={500} size="sm">Invert Control</Text>
                      <Switch 
                        checked={invertControl}
                        onChange={(event) => setInvertControl(event.currentTarget.checked)}
                        color="amber"
                        size="md"
                        thumbIcon={
                          invertControl ? (
                            <i className="fa-solid fa-check" style={{ color: '#000', fontSize: '0.6rem' }} />
                          ) : (
                            <i className="fa-solid fa-times" style={{ color: '#000', fontSize: '0.6rem' }} />
                          )
                        }
                      />
                    </Group>
                    <Text size="xs" c="dimmed">
                      {controlType === 'button' ? 
                        'When inverted, button press maps to maximum position instead of minimum' :
                        'When inverted, joystick movement direction is reversed'
                      }
                    </Text>
                  </Box>
                </Grid.Col>
                
                {/* Axis and Analog-button specific controls */}
                {(controlType === 'axis' || controlMode === 'absolute' || controlMode === 'relative') && (
                  <Grid.Col span={6}>
                    <Box 
                      py="xs"
                      px="md"
                      sx={{ 
                        border: '1px solid rgba(255, 179, 0, 0.2)',
                        borderRadius: 'var(--mantine-radius-md)',
                        background: 'rgba(255, 179, 0, 0.05)'
                      }}
                    >
                      <Text fw={500} size="sm" mb="xs">Sensitivity Multiplier</Text>
                      <Group spacing="xs" wrap="nowrap" align="center">
                        <i className="fa-solid fa-turtle" style={{ color: 'var(--mantine-color-dimmed)' }}></i>
                        <Slider
                          min={0.1}
                          max={5}
                          step={0.1}
                          precision={1}
                          value={multiplier}
                          onChange={setMultiplier}
                          color="amber"
                          style={{ flex: 1 }}
                          size="sm"
                          marks={[
                            { value: 0.1, label: '0.1' },
                            { value: 1, label: '1' },
                            { value: 5, label: '5' }
                          ]}
                        />
                        <i className="fa-solid fa-rabbit" style={{ color: 'var(--mantine-color-dimmed)' }}></i>
                      </Group>
                      <Text size="xs" c="dimmed" mt="xs">
                        Higher values = more sensitive {controlType === 'axis' ? 'joystick' : 'button'} response
                      </Text>
                    </Box>
                  </Grid.Col>
                )}
              </Grid>
              
              {/* Control mode selection */}
              <Box>
                <Text fw={500} size="sm" mb="xs">Control Mode</Text>
                <Paper withBorder={true} p="md" radius="md">
                  {controlType === 'button' ? (
                    /* Button modes */
                    <Radio.Group
                      value={controlMode}
                      onChange={(value) => {
                        setControlMode(value);
                        // If switching to an analog mode, ensure the control type is axis
                        if (value === 'absolute' || value === 'relative') {
                          setControlType('axis');
                        }
                      }}
                      name="controlMode"
                      withAsterisk
                    >
                      <Stack spacing="xs">
                        <Group mt="xs">
                          <Radio
                            value="toggle"
                            label={
                              <Box>
                                <Text>Toggle (Solid State)</Text>
                                <Text size="xs" c="dimmed">Button press toggles between min and max position</Text>
                              </Box>
                            }
                          />
                          <Radio
                            value="momentary"
                            label={
                              <Box>
                                <Text>Momentary</Text>
                                <Text size="xs" c="dimmed">Button held = min position, released = max position (or inverted)</Text>
                              </Box>
                            }
                          />
                        </Group>
                        <Divider label="Analog Button Modes" labelPosition="center" size="xs" />
                        <Group mt="xs">
                          <Radio
                            value="absolute"
                            label={
                              <Box>
                                <Text>Absolute (Analog)</Text>
                                <Text size="xs" c="dimmed">Button pressure directly maps to servo position</Text>
                              </Box>
                            }
                          />
                          <Radio
                            value="relative"
                            label={
                              <Box>
                                <Text>Relative (Analog)</Text>
                                <Text size="xs" c="dimmed">Button changes position gradually based on pressure</Text>
                              </Box>
                            }
                          />
                        </Group>
                      </Stack>
                    </Radio.Group>
                  ) : (
                    /* Axis modes */
                    <Radio.Group
                      value={controlMode}
                      onChange={setControlMode}
                      name="controlMode"
                      withAsterisk
                    >
                      <Group mt="xs">
                        <Radio
                          value="absolute"
                          label={
                            <Box>
                              <Text>Absolute</Text>
                              <Text size="xs" c="dimmed">Joystick position directly maps to servo position</Text>
                            </Box>
                          }
                        />
                        <Radio
                          value="relative"
                          label={
                            <Box>
                              <Text>Relative</Text>
                              <Text size="xs" c="dimmed">Joystick changes position gradually based on multiplier</Text>
                            </Box>
                          }
                        />
                      </Group>
                    </Radio.Group>
                  )}
                </Paper>
              </Box>
            </>
          )}
          
          {/* Status of gamepad control attachment */}
          {servo?.attached_control && (
            <Paper p="md" withBorder={true} radius="md" bg="rgba(76, 175, 80, 0.05)">
              <Stack spacing="xs">
                <Group spacing={6}>
                  <i className="fa-solid fa-check-circle" style={{ color: '#4CAF50' }}></i>
                  <Text fw={500}>Current Configuration</Text>
                </Group>
                <Table striped withColumnBorders={true} size="xs">
                  <Table.Tbody>
                    <Table.Tr>
                      <Table.Td fw={500}>Control</Table.Td>
                      <Table.Td>{servo.attached_control}</Table.Td>
                    </Table.Tr>
                    {servo.gamepad_config && (
                      <>
                        <Table.Tr>
                          <Table.Td fw={500}>Type</Table.Td>
                          <Table.Td style={{ textTransform: 'capitalize' }}>{servo.gamepad_config.type || 'Button'}</Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td fw={500}>Mode</Table.Td>
                          <Table.Td style={{ textTransform: 'capitalize' }}>{servo.gamepad_config.mode || 'Toggle'}</Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td fw={500}>Inverted</Table.Td>
                          <Table.Td>{servo.gamepad_config.invert ? 'Yes' : 'No'}</Table.Td>
                        </Table.Tr>
                        {(servo.gamepad_config.type === 'axis' || 
                         servo.gamepad_config.mode === 'absolute' || 
                         servo.gamepad_config.mode === 'relative') && (
                          <Table.Tr>
                            <Table.Td fw={500}>Multiplier</Table.Td>
                            <Table.Td>{servo.gamepad_config.multiplier || 1}</Table.Td>
                          </Table.Tr>
                        )}
                      </>
                    )}
                  </Table.Tbody>
                </Table>
              </Stack>
            </Paper>
          )}
          
          <Group position="right" mt="md">
            {servo?.attached_control && (
              <Button 
                variant="outline"
                color="red"
                onClick={() => {
                  // Update the UI state first for a responsive feel
                  const updatedServo = { ...servo };
                  updatedServo.attached_control = "";
                  updatedServo.gamepad_config = {};
                  setServo(updatedServo);
                  
                  // Clear the form state as well
                  setAttachIndex("");
                  setControlType("");
                  setControlMode("");
                  setInvertControl(false);
                  setMultiplier(1);
                  
                  // Then send the event to the server
                  node.emit('detach_servo', [parseInt(id)]);
                  showToast('Servo detached from gamepad control');
                  setOpenedModal(null);
                }}
                leftSection={<i className="fa-solid fa-unlink"></i>}
              >
                Detach Control
              </Button>
            )}
            <Button 
              variant="outline" 
              color="gray" 
              onClick={() => setOpenedModal(null)}
            >
              Cancel
            </Button>
            <Button 
              variant="filled" 
              color="amber" 
              onClick={() => {
                handleAttachServo();
                setOpenedModal(null);
              }}
              disabled={!attachIndex || !controlType || !controlMode}
            >
              Save Mapping
            </Button>
          </Group>
        </Stack>
      </Modal>
      
      {/* Advanced Settings Modal */}
      <Modal
        opened={openedModal === 'advanced'}
        onClose={() => setOpenedModal(null)}
        title={<Text fw={600} c="amber">Advanced Servo Settings</Text>}
        size="lg"
        centered
        overlayProps={{
          color: 'rgb(0, 0, 0)',
          opacity: 0.55,
          blur: 3,
        }}
      >
        <Stack spacing="md">
          {/* Min/Max Pulse Settings */}
          <Box>
            <Text fw={500} mb="xs">Servo Pulse Range</Text>
            <Grid>
              <Grid.Col span={6}>
                <NumberInput
                  label="Min Pulse"
                  description="Minimum position (0-1023)"
                  min={0}
                  max={1023}
                  value={servo?.min_pulse !== undefined ? servo.min_pulse : 0}
                  onChange={(val) => {
                    if (val !== null) {
                      node.emit('update_servo_setting', [{
                        id: parseInt(id),
                        property: "min_pulse",
                        value: parseInt(val)
                      }]);
                      showToast(`Min pulse set to ${val}`);
                    }
                  }}
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <NumberInput
                  label="Max Pulse"
                  description="Maximum position (0-1023)"
                  min={0}
                  max={1023}
                  value={servo?.max_pulse !== undefined ? servo.max_pulse : 1023}
                  onChange={(val) => {
                    if (val !== null) {
                      node.emit('update_servo_setting', [{
                        id: parseInt(id),
                        property: "max_pulse",
                        value: parseInt(val)
                      }]);
                      showToast(`Max pulse set to ${val}`);
                    }
                  }}
                />
              </Grid.Col>
            </Grid>
            <Text size="xs" c="dimmed" mt={5}>
              These values represent the absolute minimum and maximum positions 
              that the servo can move to. Valid range is 0-1023.
            </Text>
          </Box>
          
          <Divider my="md" label="Danger Zone" labelPosition="center" color="red" />
          
          <Paper p="md" withBorder={true} radius="md" bg="rgba(244, 67, 54, 0.05)" style={{ border: '1px dashed rgba(244, 67, 54, 0.3)' }}>
            <Stack spacing="xs">
              <Text size="sm" c="red" fw={500} align="center">Reset Servo Configuration</Text>
              <Text size="xs" c="dimmed" align="center">
                This will reset all servo settings to factory defaults including calibration, 
                range values, alias, and gamepad mappings.
              </Text>
              <Button 
                variant="outline"
                color="red"
                onClick={() => {
                  handleResetServo();
                  setOpenedModal(null);
                }}
                fullWidth
                leftSection={<i className="fa-solid fa-rotate-left"></i>}
                mt="xs"
              >
                Reset to Factory Defaults
              </Button>
            </Stack>
          </Paper>
          
          <Group position="right" mt="md">
            <Button 
              variant="outline" 
              color="gray" 
              onClick={() => setOpenedModal(null)}
            >
              Close
            </Button>
          </Group>
        </Stack>
      </Modal>
      
      {/* CSS is now handled through Mantine's styling system */}
    </Container>
  );
};

export default ServoDebugView;