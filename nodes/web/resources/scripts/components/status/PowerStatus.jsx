/**
 * PowerStatus Component
 * 
 * Displays power status information for the robot.
 * Shows battery level, voltage, current, power consumption, and estimated runtime.
 * Includes battery capacity estimation and discharge rate information.
 * 
 * @component
 */
import React, { useState, useEffect, useRef } from 'react';
import { 
  Group, 
  Menu, 
  UnstyledButton, 
  Text, 
  Stack, 
  Box, 
  rem 
} from '@mantine/core';
import node from '../../Node';

const PowerStatus = () => {
  const [voltage, setVoltage] = useState('');
  const [current, setCurrent] = useState('');
  const [power, setPower] = useState('');
  const [runtime, setRuntime] = useState('');
  const [soc, setSoc] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [capacity, setCapacity] = useState(2.5); // Default capacity in Ah
  const [dischargeRate, setDischargeRate] = useState(0); // % per hour
  const menuRef = useRef(null);

  useEffect(() => {
    // Subscribe to battery/power events
    const voltageUnsub = node.on('voltage', (event) => {
      setVoltage(parseFloat(event.value).toFixed(2));
    });
    
    const currentUnsub = node.on('current', (event) => {
      setCurrent(parseFloat(event.value).toFixed(2));
    });
    
    const powerUnsub = node.on('power', (event) => {
      setPower(parseFloat(event.value).toFixed(2));
    });
    
    const socUnsub = node.on('soc', (event) => {
      setSoc(parseFloat(event.value).toFixed(0));
    });
    
    const runtimeUnsub = node.on('runtime', (event) => {
      console.log("Raw runtime event:", event);
      
      // Handle array values (most likely case from pyarrow)
      let runtimeValue;
      if (Array.isArray(event.value)) {
        runtimeValue = event.value[0];
      } else {
        runtimeValue = event.value;
      }
      
      // Convert to number and validate
      runtimeValue = parseFloat(runtimeValue);
      
      // If not a valid number, use 0
      if (isNaN(runtimeValue) || !isFinite(runtimeValue) || runtimeValue < 0) {
        runtimeValue = 0;
      }
      
      console.log("Processed runtime:", runtimeValue);
      setRuntime(runtimeValue);
    });
    
    // Subscribe to new capacity and discharge rate events
    const capacityUnsub = node.on('capacity', (event) => {
      setCapacity(parseFloat(event.value).toFixed(2));
    });
    
    const dischargeRateUnsub = node.on('discharge_rate', (event) => {
      setDischargeRate(parseFloat(event.value).toFixed(1));
    });
    
    // Cleanup subscriptions
    return () => {
      voltageUnsub();
      currentUnsub();
      powerUnsub();
      socUnsub();
      runtimeUnsub();
      capacityUnsub();
      dischargeRateUnsub();
    };
  }, []);
  
  // Function to determine which battery icon to show based on SOC
  const getBatteryIcon = () => {
    const socNumber = parseInt(soc) || 0;
    
    if (socNumber <= 0) return 'fa-battery-empty';
    if (socNumber <= 20) return 'fa-battery-quarter';
    if (socNumber <= 50) return 'fa-battery-half';
    if (socNumber <= 80) return 'fa-battery-three-quarters';
    return 'fa-battery-full';
  };
  
  // Function to determine battery status color
  const getBatteryStatusColor = () => {
    const socNumber = parseInt(soc) || 0;
    
    if (socNumber <= 20) return 'red';
    if (socNumber <= 50) return 'amber';
    return 'green';
  };
  
  // Format runtime from seconds to HH:MM format
  const formatRuntime = (seconds) => {
    console.log("Formatting runtime:", seconds, "Type:", typeof seconds);
    
    // Handle all possible invalid cases
    if (seconds === Infinity || seconds === "Infinity" || 
        isNaN(seconds) || seconds <= 0 || seconds === undefined) {
      return "--:--";
    }
    
    // Ensure seconds is a number
    const secondsNum = Number(seconds);
    
    const hours = Math.floor(secondsNum / 3600);
    const minutes = Math.floor((secondsNum % 3600) / 60);
    console.log("Formatted runtime:", hours, ":", minutes);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
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
        <UnstyledButton
          aria-label="Battery Status"
          onClick={() => setIsOpen(!isOpen)}
          style={{ padding: '6px 8px' }}
        >
          <Group spacing={4}>
            <i 
              className={`fa-solid ${getBatteryIcon()}`} 
              style={{ color: `var(--mantine-color-${getBatteryStatusColor()}-6)` }}
            ></i>
            <Text size="sm" fw={500}>{soc}%</Text>
          </Group>
        </UnstyledButton>
      </Menu.Target>

      <Menu.Dropdown>
        <Box p="xs">
          <Stack spacing="xs">
            <Group spacing="xs">
              <i className="fa-solid fa-bolt" style={{ color: 'var(--mantine-color-amber-6)', width: rem(20) }}></i>
              <Text size="sm">Voltage: {voltage} V</Text>
            </Group>
            <Group spacing="xs">
              <i className="fa-solid fa-gauge-high" style={{ color: 'var(--mantine-color-amber-6)', width: rem(20) }}></i>
              <Text size="sm">Current: {current} A</Text>
            </Group>
            <Group spacing="xs">
              <i className="fa-solid fa-plug" style={{ color: 'var(--mantine-color-amber-6)', width: rem(20) }}></i>
              <Text size="sm">Power: {power} W</Text>
            </Group>
            <Group spacing="xs">
              <i className="fa-solid fa-clock" style={{ color: 'var(--mantine-color-amber-6)', width: rem(20) }}></i>
              <Text size="sm">Runtime: {formatRuntime(runtime)}</Text>
            </Group>
            <Group spacing="xs">
              <i className="fa-solid fa-battery-full" style={{ color: 'var(--mantine-color-amber-6)', width: rem(20) }}></i>
              <Text size="sm">Capacity: {capacity} Ah</Text>
            </Group>
            <Group spacing="xs">
              <i className="fa-solid fa-arrow-trend-down" style={{ color: 'var(--mantine-color-amber-6)', width: rem(20) }}></i>
              <Text size="sm">Discharge: {dischargeRate}%/hr</Text>
            </Group>
          </Stack>
        </Box>
      </Menu.Dropdown>
    </Menu>
  );
};

export default PowerStatus;