/**
 * VolumeControl Component
 * 
 * A control for adjusting the audio volume.
 * Provides a popup with a vertical slider to adjust the volume level.
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
  Center,
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
      width={90}
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
        <Box py="xs" px="md">
          <Stack align="center" justify="center" gap="xs">
            <Text size="sm" c="amber" fw={500}>
              Volume
            </Text>
            
            <Center h={200}>
              <Slider
                value={volume}
                onChange={handleVolumeChange}
                min={0}
                max={100}
                step={5}
                color="amber"
                label={null}
                size="md"
                thumbSize={18}
                orientation="vertical"
                h={180}
                styles={{
                  root: { height: 180 },
                  track: { width: 8 },
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
                    transform: 'translateX(-2px) translateY(-2px)',
                    borderColor: 'var(--mantine-color-amber-filled)'
                  }
                }}
                marks={[
                  { value: 0, label: '0%' },
                  { value: 50, label: '50%' },
                  { value: 100, label: '100%' }
                ]}
              />
            </Center>
            
            <Box mt={4}>
              <Text size="sm" ta="center" c="dimmed">
                {volume}%
              </Text>
            </Box>
          </Stack>
        </Box>
      </Popover.Dropdown>
    </Popover>
  );
};

export default VolumeControl;