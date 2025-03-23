/**
 * VolumeControl Component
 * 
 * A control for adjusting the audio volume.
 * Provides a dropdown with a slider to adjust the volume level.
 * 
 * @component
 */
import React, { useState } from 'react';
import { 
  Menu, 
  ActionIcon, 
  Slider, 
  Text, 
  Stack, 
  Box 
} from '@mantine/core';
import node from '../../Node';

const VolumeControl = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [volume, setVolume] = useState(50);
  
  const handleVolumeChange = (newVolume) => {
    setVolume(newVolume);
    node.emit('set_volume', [newVolume]);
  };

  const getVolumeIcon = () => {
    // Using class names that match Font Awesome
    if (volume <= 0) return 'fa-volume-off';
    if (volume <= 30) return 'fa-volume-down';
    if (volume <= 70) return 'fa-volume-down';
    return 'fa-volume-up';
  };

  return (
    <Menu
      opened={isOpen}
      onChange={setIsOpen}
      position="bottom-end"
      shadow="md"
      width={200}
      withArrow
    >
      <Menu.Target>
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
      </Menu.Target>
      
      <Menu.Dropdown>
        <Box p="md">
          <Stack spacing="xs">
            <Slider
              value={volume}
              onChange={handleVolumeChange}
              min={0}
              max={100}
              step={1}
              color="amber"
              label={(value) => `${value}%`}
              labelAlwaysOn
              size="md"
            />
            <Text size="sm" ta="center" c="dimmed">
              Volume: {volume}%
            </Text>
          </Stack>
        </Box>
      </Menu.Dropdown>
    </Menu>
  );
};

export default VolumeControl;