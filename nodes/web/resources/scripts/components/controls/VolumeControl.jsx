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

const VolumeControl = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [volume, setVolume] = useState(50);
  
  // Initial volume fetch could be added here if the backend supports it
  useEffect(() => {
    // Emit initial volume when component mounts
    node.emit('set_volume', [volume]);
  }, []);
  
  const handleVolumeChange = (newVolume) => {
    setVolume(newVolume);
    node.emit('set_volume', [newVolume]);
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
        >
          <i 
            className={`fa-solid ${getVolumeIcon()}`}
            style={{ color: 'var(--mantine-color-amber-6)' }}
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