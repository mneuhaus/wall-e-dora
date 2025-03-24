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
import { CircularSliderWithChildren } from 'react-circular-slider-svg';

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
  Notification,
  Table,
  rem,
  Tooltip
} from '@mantine/core';

const ServoDebugView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [servo, setServo] = useState(null);
  const [position, setPosition] = useState(0);
  const [displayPosition, setDisplayPosition] = useState(0); // For UI display (0-300 degrees)
  const [speed, setSpeed] = useState(null); // Start with null so we know when it's initialized from server
  const [sliderReady, setSliderReady] = useState(false); // Track if slider should be rendered
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(1023);
  const [aliasInput, setAliasInput] = useState('');
  const [attachIndex, setAttachIndex] = useState("");
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [openedModal, setOpenedModal] = useState(null); // For tracking which modal is open
  const [isToastVisible, setIsToastVisible] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState('success');
  const positionUpdateTimeout = useRef(null);

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
      console.warn('Invalid servoPos:', servoPos);
      return 0;
    }
    
    if (servoMin === null || servoMin === undefined || typeof servoMin !== 'number' || isNaN(servoMin)) {
      console.warn('Invalid servoMin:', servoMin);
      servoMin = 0; // Default min
    }
    
    if (servoMax === null || servoMax === undefined || typeof servoMax !== 'number' || isNaN(servoMax)) {
      console.warn('Invalid servoMax:', servoMax);
      servoMax = 1023; // Default max
    }
    
    // Ensure min and max are valid
    if (servoMin < 0) servoMin = 0;
    if (servoMax > 1023) servoMax = 1023;
    if (servoMax <= servoMin) {
      console.warn('Invalid range: servoMax must be greater than servoMin', 'servoMin:', servoMin, 'servoMax:', servoMax);
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
      console.warn('Invalid uiPos:', uiPos);
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
  
  // Debug modal state changes
  useEffect(() => {
    console.log('Modal state changed:', openedModal);
  }, [openedModal]);

  useEffect(() => {
    console.log(`ServoDebugView initialized for servo ${id}`);
    
    // Function to process servo data (reused for both event types)
    const processServoData = (servoInfo) => {
      if (!servoInfo) return;
      
      console.log(`Processing servo data for ID ${id}:`, servoInfo);
      setServo(servoInfo);
      
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
        console.warn('Invalid UI position calculated:', uiPosition);
        setDisplayPosition(0); // Default to 0 if invalid
        // Even with invalid position, we should still render the slider
        if (!sliderReady) {
          setTimeout(() => setSliderReady(true), 50);
        }
      }
      
      // Set speed - IMPORTANT: This needs to work on page load
      if (servoInfo.speed !== undefined && servoInfo.speed !== null) {
        console.log(`Setting speed to ${servoInfo.speed} from servo data`);
        setSpeed(Number(servoInfo.speed));
      } else {
        console.log("No speed in servo data, using default 1000");
        setSpeed(1000);
      }
      
      // Update alias input if it's empty and the servo has an alias
      if (aliasInput === '' && servoInfo.alias) {
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
      console.log(`Received servos_list, looking for servo ID ${id}`, servosList);
      const currentServo = servosList.find(s => s.id === parseInt(id));
      if (currentServo) {
        console.log(`Found servo ${id} in servos_list:`, currentServo);
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
      console.warn('Invalid position received in handlePositionChange:', newPosition);
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
      console.warn('Invalid min value in handlePositionChange, using default 0:', servoMin);
      servoMin = 0;
    }
    
    if (servoMax === null || servoMax === undefined || typeof servoMax !== 'number' || isNaN(servoMax)) {
      console.warn('Invalid max value in handlePositionChange, using default 1023:', servoMax);
      servoMax = 1023;
    }
    
    // Ensure min/max are valid
    if (servoMin < 0) servoMin = 0;
    if (servoMax > 1023) servoMax = 1023;
    if (servoMax <= servoMin) {
      console.warn('Invalid range in handlePositionChange: max <= min. Using defaults.', servoMin, servoMax);
      servoMin = 0;
      servoMax = 1023;
    }
    
    // Map UI range (0-300) to servo range (min-max)
    const servoPosition = mapUIToServo(newPosition, servoMin, servoMax);
    
    // Validate servoPosition before setting it
    if (servoPosition === null || servoPosition === undefined || 
        typeof servoPosition !== 'number' || isNaN(servoPosition)) {
      console.warn('Invalid servoPosition calculated:', servoPosition);
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
    
    // Use the new servo-specific setting update endpoint
    node.emit('update_servo_setting', [{
      id: servoId,
      property: "alias",
      value: aliasInput.trim()
    }]);
    
    showToast(`Alias set to "${aliasInput}"`);
  };
  
  const handleAttachServo = () => {
    if (!attachIndex) return;
    
    // Update to use update_servo_setting
    node.emit('update_servo_setting', [{
      id: parseInt(id),
      property: "attached_control",
      value: attachIndex
    }]);
    showToast(`Attached to gamepad control: ${attachIndex}`);
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
        invert: false
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
    <Container size="xl" py="md">
      <Paper p="md" radius="md" withBorder>
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
  
  const servoStatus = {
    Position: position || 'N/A',
    Speed: speed || 'N/A',
    Alias: servo.alias || 'None',
    'Min Pulse': servo.min_pulse !== undefined ? servo.min_pulse : 'Not calibrated',
    'Max Pulse': servo.max_pulse !== undefined ? servo.max_pulse : 'Not calibrated',
    'Calibrated': servo.calibrated ? 'Yes' : 'No',
    'Inverted': servo.invert ? 'Yes' : 'No',
    'Attached Control': servo.attached_control || 'None'
  };
  
  return (
    <Container size="xl" py="md">
      {/* Toast notification */}
      {isToastVisible && (
        <Notification
          color={getToastColor(toastType)}
          title={toastType.charAt(0).toUpperCase() + toastType.slice(1)}
          onClose={() => setIsToastVisible(false)}
          withCloseButton
          withBorder
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
      
      <Paper radius="md" withBorder p={0}>
        {/* Header Section */}
        <Box py="xs" px="md" bg="rgba(255, 215, 0, 0.05)" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
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
                  onClick={() => {
                    console.log('Opening alias modal');
                    setOpenedModal('alias');
                    console.log('Modal state after set:', 'alias');
                  }}
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
        
        <Box p="md">
          <Grid gutter="md">
            {/* Control Card */}
            <Grid.Col span={{ base: 12, md: 7 }}>
              <Paper radius="md" withBorder shadow="sm" h="100%" style={{ display: 'flex', flexDirection: 'column' }}>
                <Box 
                  py="xs" 
                  px="md" 
                  bg="rgba(255, 215, 0, 0.05)" 
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <Group>
                    <i className="fa-solid fa-sliders-h" style={{ color: '#FFB300' }}></i>
                    <Title order={5} c="amber" style={{ marginTop: 0 }}>Control</Title>
                  </Group>
                </Box>
                
                <Stack p="xs" align="center" style={{ flex: 1 }}>
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
                        size={220}
                        minValue={0}
                        maxValue={300}
                        startAngle={0}
                        endAngle={300}
                        handleSize={18}
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
                            marginTop: '10px'
                          }}
                        >
                          <Text size="28px" fw={700} c="amber" lh={1}>
                            {typeof displayPosition === 'number' && !isNaN(displayPosition) ? 
                              `${displayPosition}°` : 
                              '0°'
                            }
                          </Text>
                          <Text size="sm" c="dimmed" lh={1} mb={8}>angle</Text>
                          <Badge color="amber" variant="light" size="sm" radius="sm" px={8} py={4} 
                            sx={{ 
                              boxShadow: "0 0 4px rgba(255, 179, 0, 0.4)",
                              background: "rgba(255, 179, 0, 0.1)",
                              border: "1px solid rgba(255, 179, 0, 0.3)"
                            }}
                          >
                            {position || '0'}
                          </Badge>
                          <Text size="sm" c="dimmed" lh={1} mt={4}>pulse</Text>
                        </div>
                      </CircularSliderWithChildren>
                    ) : (
                      <Box 
                        style={{ 
                          width: 220, 
                          height: 220, 
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
                            width: rem(48),
                            height: rem(48),
                            border: '4px solid rgba(255, 255, 255, 0.1)',
                            borderTop: '4px solid var(--mantine-color-amber-5)',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite',
                            marginBottom: rem(10)
                          }}
                        ></Box>
                        <Text size="sm" c="dimmed" lh={1}>Loading...</Text>
                      </Box>
                    )}
                  </Box>
                  
                  <Box w="100%" mt={10}>
                    <Group justify="space-between" mb={2}>
                      <Text size="sm" fw={500}>Speed Control</Text>
                      <Badge color="amber" variant="filled" size="sm" 
                        style={{
                          boxShadow: "0 0 8px rgba(255, 179, 0, 0.4)",
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
                        step={10}
                        value={speed}
                        onChange={handleSpeedChange}
                        onChangeEnd={handleSpeedChangeComplete}
                        color="amber"
                        labelAlwaysOn={false}
                        size="sm"
                      />
                    ) : (
                      <div style={{ height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--mantine-color-dimmed)' }}>Loading...</span>
                      </div>
                    )}
                    <Text size="xs" c="dimmed" mt={1} mb={0}>Lower values = faster movement</Text>
                  </Box>
                </Stack>
              </Paper>
            </Grid.Col>
          
            {/* Info Card */}
            <Grid.Col span={{ base: 12, md: 5 }}>
              <Paper radius="md" withBorder shadow="sm" h="100%" style={{ display: 'flex', flexDirection: 'column' }}>
                <Box 
                  py="xs" 
                  px="md" 
                  bg="rgba(255, 215, 0, 0.05)" 
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <Group>
                    <i className="fa-solid fa-info-circle" style={{ color: '#FFB300' }}></i>
                    <Title order={5} c="amber" style={{ marginTop: 0 }}>Information</Title>
                  </Group>
                </Box>
                
                <Box p="xs" style={{ flex: 1 }}>
                  <Table striped highlightOnHover withTableBorder withColumnBorders>
                    <Table.Tbody>
                      {Object.entries(servoStatus).map(([key, value]) => (
                        <Table.Tr key={key}>
                          <Table.Td style={{ fontWeight: 500, color: 'var(--mantine-color-dimmed)' }}>{key}</Table.Td>
                          <Table.Td style={{ color: 'var(--mantine-color-amber-filled)', textAlign: 'right' }}>{value}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                  
                  {servo.properties && Object.keys(servo.properties).length > 0 && (
                    <>
                      <Title order={6} c="amber" mt="md" mb="xs">Advanced Properties</Title>
                      <Table size="xs" striped highlightOnHover withTableBorder withColumnBorders>
                        <Table.Tbody>
                          {Object.entries(servo.properties).map(([key, value]) => (
                            <Table.Tr key={key}>
                              <Table.Td style={{ fontWeight: 500, color: 'var(--mantine-color-dimmed)' }}>{key}</Table.Td>
                              <Table.Td style={{ textAlign: 'right' }}>{value}</Table.Td>
                            </Table.Tr>
                          ))}
                        </Table.Tbody>
                      </Table>
                    </>
                  )}
                </Box>
              </Paper>
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
        {console.log('Modal render - opened state:', openedModal === 'alias', 'openedModal value:', openedModal)}
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
        onClose={() => setOpenedModal(null)}
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
          
          <Select
            label="Gamepad Control"
            placeholder="Choose a control"
            value={attachIndex}
            onChange={setAttachIndex}
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
          
          {/* Status of gamepad control attachment */}
          {servo?.attached_control && (
            <Paper p="xs" withBorder radius="md" bg="rgba(76, 175, 80, 0.05)">
              <Group spacing={6}>
                <i className="fa-solid fa-check-circle" style={{ color: '#4CAF50' }}></i>
                <Text component="span" size="sm">Currently attached to:</Text>
                <Text component="span" size="sm" c="amber" fw={500}>{servo.attached_control}</Text>
              </Group>
            </Paper>
          )}
          
          <Group position="right" mt="md">
            {servo?.attached_control && (
              <Button 
                variant="outline"
                color="red"
                onClick={() => {
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
              disabled={!attachIndex}
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
          
          <Paper p="md" withBorder radius="md" bg="rgba(244, 67, 54, 0.05)" style={{ border: '1px dashed rgba(244, 67, 54, 0.3)' }}>
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