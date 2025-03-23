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
import CircularSlider from 'react-circular-slider-svg';

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
  Collapse,
  Notification,
  Table,
  rem
} from '@mantine/core';

const ServoDebugView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [servo, setServo] = useState(null);
  const [position, setPosition] = useState(0);
  const [displayPosition, setDisplayPosition] = useState(0); // For UI display (0-300 degrees)
  const [speed, setSpeed] = useState(null); // Start with null so we know when it's initialized from server
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(4095);
  const [newId, setNewId] = useState('');
  const [aliasInput, setAliasInput] = useState('');
  const [attachIndex, setAttachIndex] = useState("");
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [showAdvancedControls, setShowAdvancedControls] = useState(false);
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
      return 0;
    }
    
    if (servoMax === null || servoMax === undefined || typeof servoMax !== 'number' || isNaN(servoMax)) {
      console.warn('Invalid servoMax:', servoMax);
      return 0;
    }
    
    // Ensure min and max are valid
    if (servoMax <= servoMin) {
      console.warn('Invalid range: servoMax must be greater than servoMin', 'servoMin:', servoMin, 'servoMax:', servoMax);
      return 0;
    }
    
    return Math.round(300 * (servoPos - servoMin) / (servoMax - servoMin));
  }, []);
  
  // Helper function to map UI angle to servo position
  const mapUIToServo = useCallback((uiPos, servoMin, servoMax) => {
    // Validate inputs to prevent NaN
    if (uiPos === null || uiPos === undefined || typeof uiPos !== 'number' || isNaN(uiPos)) {
      console.warn('Invalid uiPos:', uiPos);
      return 0; // Default to 0 if servoMin is invalid
    }
    
    if (servoMin === null || servoMin === undefined || typeof servoMin !== 'number' || isNaN(servoMin)) {
      console.warn('Invalid servoMin:', servoMin);
      return 0;
    }
    
    if (servoMax === null || servoMax === undefined || typeof servoMax !== 'number' || isNaN(servoMax)) {
      console.warn('Invalid servoMax:', servoMax);
      return servoMin || 0;
    }
    
    // Ensure min and max are valid
    if (servoMax <= servoMin) {
      console.warn('Invalid range: servoMax must be greater than servoMin', 'servoMin:', servoMin, 'servoMax:', servoMax);
      return servoMin;
    }
    
    return Math.round(servoMin + (uiPos / 300) * (servoMax - servoMin));
  }, []);

  useEffect(() => {
    console.log(`ServoDebugView initialized for servo ${id}`);
    
    // Function to process servo data (reused for both event types)
    const processServoData = (servoInfo) => {
      if (!servoInfo) return;
      
      console.log(`Processing servo data for ID ${id}:`, servoInfo);
      setServo(servoInfo);
      
      // Get min/max pulse values with validation
      let servoMinPulse = 500;
      if (servoInfo.min_pulse !== undefined && servoInfo.min_pulse !== null && !isNaN(servoInfo.min_pulse)) {
        servoMinPulse = Number(servoInfo.min_pulse);
      }
      
      let servoMaxPulse = 2500;
      if (servoInfo.max_pulse !== undefined && servoInfo.max_pulse !== null && !isNaN(servoInfo.max_pulse)) {
        servoMaxPulse = Number(servoInfo.max_pulse);
      }
      
      // Ensure max > min
      if (servoMaxPulse <= servoMinPulse) {
        console.warn('Invalid servo range: max <= min, using default values');
        servoMinPulse = 500;
        servoMaxPulse = 2500;
      }
      
      setMin(servoMinPulse);
      setMax(servoMaxPulse);
      
      // Get current servo position with validation
      let servoPosition = 0;
      if (servoInfo.position !== undefined && servoInfo.position !== null && !isNaN(servoInfo.position)) {
        servoPosition = Number(servoInfo.position);
      }
      
      // Set raw position value
      setPosition(servoPosition);
      
      // Map servo position to UI range (0-300 degrees)
      const uiPosition = mapServoToUI(servoPosition, servoMinPulse, servoMaxPulse);
      
      // Validate before setting
      if (typeof uiPosition === 'number' && !isNaN(uiPosition)) {
        setDisplayPosition(uiPosition);
      } else {
        console.warn('Invalid UI position calculated:', uiPosition);
        setDisplayPosition(0); // Default to 0 if invalid
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
    
    // Update display position immediately for responsive UI
    setDisplayPosition(newPosition);
    
    // Validate min and max before passing to mapUIToServo
    if (min === null || min === undefined || typeof min !== 'number' || isNaN(min)) {
      console.warn('Invalid min value in handlePositionChange:', min);
      return;
    }
    
    if (max === null || max === undefined || typeof max !== 'number' || isNaN(max)) {
      console.warn('Invalid max value in handlePositionChange:', max);
      return;
    }
    
    // Map UI range (0-300) to servo range (min-max)
    const servoPosition = mapUIToServo(newPosition, min, max);
    
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
  
  const handleChangeId = () => {
    if (newId.trim() === '') return;
    
    const newIdInt = parseInt(newId);
    if (isNaN(newIdInt) || newIdInt < 1 || newIdInt > 31) {
      showToast('ID must be between 1 and 31', 'error');
      return;
    }
    
    // Confirm before changing ID
    if (window.confirm(`Are you sure you want to change the servo ID from ${id} to ${newId}? You'll be redirected to the new servo page.`)) {
      // Using update_servo_setting now
      node.emit('update_servo_setting', [{
        id: parseInt(id),
        property: "id",
        value: newIdInt
      }]);
      setNewId('');
      showToast(`Changing servo ID to ${newId}...`);
      
      // Navigate to the new servo page after a short delay
      setTimeout(() => {
        navigate(`/servo/${newId}`);
      }, 1500);
    }
  };
  
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
        min_pulse: 500,
        max_pulse: 2500,
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
          </Group>
        </Box>
        
        <Box p="md">
          <Grid gutter="md">
            {/* Control Card */}
            <Grid.Col span={{ base: 12, md: 4 }}>
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
                    {/* Ensure displayPosition is a valid number */}
                    {typeof displayPosition === 'number' && !isNaN(displayPosition) ? (
                      <CircularSlider
                        size={180}
                        minValue={0}
                        maxValue={300}
                        startAngle={0}
                        endAngle={300}
                        handleSize={16}
                        handle1={{
                          value: displayPosition,
                          onChange: handlePositionChange
                        }}
                        arcColor="#FFB300"
                        arcBackgroundColor="rgba(255, 179, 0, 0.15)"
                        coerceToInt={true}
                        handleColor="#FFB300"
                        labelColor="#FFB300"
                        labelFontSize="1rem"
                        data={[]}
                        label="Position"
                      />
                    ) : (
                      <Box 
                        style={{ 
                          width: 180, 
                          height: 180, 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center',
                          border: '2px solid rgba(255, 179, 0, 0.3)',
                          borderRadius: '50%',
                          color: 'var(--mantine-color-dimmed)',
                          background: 'rgba(255, 179, 0, 0.05)'
                        }}
                      >
                        <Box 
                          sx={{
                            width: rem(32),
                            height: rem(32),
                            border: '3px solid rgba(255, 255, 255, 0.1)',
                            borderTop: '3px solid var(--mantine-color-amber-5)',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite',
                          }}
                        ></Box>
                      </Box>
                    )}
                    
                    <Stack align="center" spacing={2} mt="xs">
                      <Text size="lg" fw={600} c="amber">
                        {typeof displayPosition === 'number' && !isNaN(displayPosition) ? 
                          `${displayPosition}°` : 
                          '0°'
                        }
                      </Text>
                      <Text size="xs" c="dimmed">Servo Angle</Text>
                      <Badge color="amber" variant="light" size="sm">
                        {position || '0'} pulse
                      </Badge>
                    </Stack>
                  </Box>
                  
                  <Box w="100%" py="xs">
                    <Group justify="space-between" mb={4}>
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
                    <Text size="xs" c="dimmed" mt={2}>Lower values = faster movement</Text>
                  </Box>
                  
                  <Group grow w="100%" mt="xs">
                    <Button 
                      variant={isTesting ? "filled" : "outline"}
                      color="amber"
                      onClick={handleWiggle}
                      disabled={isTesting}
                      leftSection={<i className="fa-solid fa-arrows-left-right"></i>}
                      size="xs"
                    >
                      Test
                    </Button>
                    <Button 
                      variant={isCalibrating ? "filled" : "outline"}
                      color="amber"
                      onClick={handleCalibrate}
                      disabled={isCalibrating}
                      leftSection={<i className="fa-solid fa-ruler"></i>}
                      size="xs"
                    >
                      Calibrate
                    </Button>
                  </Group>
                </Stack>
              </Paper>
            </Grid.Col>
          
            {/* Settings Card (includes Gamepad) */}
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Paper radius="md" withBorder shadow="sm" h="100%" style={{ display: 'flex', flexDirection: 'column' }}>
                <Box 
                  py="xs" 
                  px="md" 
                  bg="rgba(255, 215, 0, 0.05)" 
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <Group justify="space-between">
                    <Group>
                      <i className="fa-solid fa-cog" style={{ color: '#FFB300' }}></i>
                      <Title order={5} c="amber" style={{ marginTop: 0 }}>Settings</Title>
                    </Group>
                    <Button 
                      variant="subtle" 
                      color="amber" 
                      size="xs"
                      onClick={() => setShowAdvancedControls(!showAdvancedControls)}
                    >
                      {showAdvancedControls ? 'Hide Advanced' : 'Show Advanced'}
                    </Button>
                  </Group>
                </Box>
                
                <Stack p="xs" spacing="md" style={{ flex: 1 }}>
                  {/* Alias Input */}
                  <Box>
                    <TextInput
                      label="Servo Alias"
                      placeholder="Friendly name for this servo"
                      value={aliasInput}
                      onChange={(e) => setAliasInput(e.target.value)}
                      maxLength={20}
                    />
                    <Group position="right" mt="xs">
                      <Button 
                        variant="outline" 
                        color="amber" 
                        onClick={handleSetAlias}
                        disabled={!aliasInput.trim()}
                        leftSection={<i className="fa-solid fa-tag"></i>}
                        size="xs"
                      >
                        Set Alias
                      </Button>
                    </Group>
                  </Box>
                  
                  {/* Gamepad Controls Section */}
                  <Box>
                    <Stack spacing="xs">
                      <Group>
                        <i className="fa-solid fa-gamepad" style={{ color: '#FFB300' }}></i>
                        <Text fw={500} c="amber" style={{ marginTop: 0 }}>Gamepad Mapping</Text>
                      </Group>
                      
                      <Text size="sm" c="dimmed">Map this servo to a gamepad control for remote operation</Text>
                      
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
                      
                      <Group position="right" mt="xs">
                        <Button 
                          variant="outline" 
                          color="amber" 
                          onClick={handleAttachServo}
                          disabled={!attachIndex}
                          leftSection={<i className="fa-solid fa-gamepad"></i>}
                          size="xs"
                        >
                          Attach to Gamepad
                        </Button>
                      </Group>
                      
                      {/* Status of gamepad control attachment */}
                      {servo.attached_control 
                        ? (
                          <Group spacing={6}>
                            <i className="fa-solid fa-check-circle" style={{ color: '#4CAF50' }}></i>
                            <Text component="span" size="sm" c="dimmed" style={{ marginTop: 0 }}>Currently attached to:</Text>
                            <Text component="span" size="sm" c="amber" fw={500} style={{ marginTop: 0 }}>{servo.attached_control}</Text>
                          </Group>
                        )
                        : (
                          <Group spacing={6}>
                            <i className="fa-solid fa-info-circle"></i>
                            <Text component="span" size="sm" c="dimmed" style={{ marginTop: 0 }}>No gamepad control attached</Text>
                          </Group>
                        )
                      }
                      
                      {servo.attached_control && (
                        <Button 
                          variant="outline"
                          onClick={() => {
                            node.emit('detach_servo', [parseInt(id)]);
                            showToast('Servo detached from gamepad control');
                          }}
                          leftSection={<i className="fa-solid fa-unlink"></i>}
                          mt="xs"
                        >
                          Detach Control
                        </Button>
                      )}
                    </Stack>
                  </Box>
                  
                  {/* Advanced Settings */}
                  <Collapse in={showAdvancedControls}>
                    <Stack spacing="md" pt="sm" style={{ borderTop: '1px dashed rgba(255, 255, 255, 0.1)' }}>
                      <Box>
                        <NumberInput
                          label="Change Servo ID"
                          placeholder="New ID (1-253)"
                          min={1}
                          max={253}
                          value={newId || undefined}
                          onChange={(val) => setNewId(val?.toString() || '')}
                        />
                        <Group position="right" mt="xs">
                          <Button 
                            variant="outline" 
                            onClick={handleChangeId}
                            disabled={!newId}
                            leftSection={<i className="fa-solid fa-id-card"></i>}
                            size="xs"
                          >
                            Update ID
                          </Button>
                        </Group>
                      </Box>
                      
                      <Paper p="md" withBorder radius="md" bg="rgba(244, 67, 54, 0.05)" style={{ border: '1px dashed rgba(244, 67, 54, 0.3)' }}>
                        <Stack spacing="xs" align="center">
                          <Group spacing={4}>
                            <i className="fa-solid fa-exclamation-triangle" style={{ color: 'var(--mantine-color-red-6)' }}></i>
                            <Text size="sm" c="red" fw={500} style={{ marginTop: 0 }}>Danger Zone</Text>
                          </Group>
                          <Button 
                            variant="outline"
                            color="red"
                            onClick={handleResetServo}
                            fullWidth
                            leftSection={<i className="fa-solid fa-rotate-left"></i>}
                          >
                            Reset to Factory Defaults
                          </Button>
                        </Stack>
                      </Paper>
                    </Stack>
                  </Collapse>
                </Stack>
              </Paper>
            </Grid.Col>
          
            {/* Info Card */}
            <Grid.Col span={{ base: 12, md: 4 }}>
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
      
      {/* CSS is now handled through Mantine's styling system */}
    </Container>
  );
};

export default ServoDebugView;