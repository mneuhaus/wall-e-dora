/**
 * VolumeControl Component
 * 
 * A control for adjusting the audio volume.
 * Provides a popup with a horizontal slider to adjust the volume level.
 * 
 * @component
 */
import React, { useState, useEffect } from 'react';
import { 
  Popover,
  ActionIcon, 
  Slider, 
  Text, 
  Stack, 
  Box,
  Group,
  rem
} from '@mantine/core';
import node from '../../Node';
import { controlStyles } from '../status/controls';

const VolumeControl = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [volume, setVolume] = useState(35);
  
  // Initial volume fetch and set up listener for volume updates
  useEffect(() => {
    // Emit initial volume when component mounts (convert from percentage to float)
    node.emit('set_volume', [volume / 100]);
    
    // Listen for volume updates from the backend
    const unsubscribe = node.on('volume', (event) => {
      if (event.value && Array.isArray(event.value) && event.value.length > 0) {
        // Convert from float (0.0-1.0) to percentage (0-100)
        const newVolume = Math.round(event.value[0] * 100);
        setVolume(newVolume);
      }
    });
    
    return () => unsubscribe(); // Clean up on unmount
  }, []);
  
  const handleVolumeChange = (newVolume) => {
    setVolume(newVolume);
    // Convert percentage (0-100) to float (0.0-1.0) for the audio node
    node.emit('set_volume', [newVolume / 100]);
  };

  const getVolumeIcon = () => {
    // Using class names that match Font Awesome
    if (volume <= 0) return 'fa-volume-mute';
    if (volume <= 30) return 'fa-volume-down';
    if (volume <= 70) return 'fa-volume-down';
    return 'fa-volume-up';
  };

  return (
    <Popover
      opened={isOpen}
      onChange={setIsOpen}
      position="bottom"
      shadow="md"
      width={420}
      withArrow
      trapFocus={false}
    >
      <Popover.Target>
        <ActionIcon
          variant="transparent"
          radius="xl"
          aria-label="Volume Control"
          onClick={() => setIsOpen(!isOpen)}
          style={controlStyles.actionIcon}
        >
          <i 
            className={`fa-solid ${getVolumeIcon()}`}
            style={{ 
              color: 'var(--mantine-color-amber-6)',
              ...controlStyles.icon
            }}
          ></i>
        </ActionIcon>
      </Popover.Target>
      
      <Popover.Dropdown>
        <Box p="md">
          <Stack align="center" gap="sm">
            <Slider
              value={volume}
              onChange={handleVolumeChange}
              min={0}
              max={100}
              step={5}
              color="amber"
              label={(value) => `${value}%`}
              labelAlwaysOn
              size="lg"
              w="100%"
              thumbSize={22}
              styles={{
                track: { height: 8 },
                thumb: { 
                  borderWidth: 2,
                  backgroundColor: 'var(--mantine-color-dark-7)',
                  borderColor: 'var(--mantine-color-amber-filled)'
                },
                markLabel: {
                  fontSize: rem(10),
                  color: 'var(--mantine-color-dimmed)'
                },
                mark: {
                  width: 4,
                  height: 4,
                  borderRadius: 4,
                  borderColor: 'var(--mantine-color-amber-filled)'
                }
              }}
            />
          </Stack>
        </Box>
      </Popover.Dropdown>
    </Popover>
  );
};

export default VolumeControl;