/**
 * VolumeControl Component
 * 
 * A control for adjusting the audio volume.
 * Provides a dropdown with a vertical slider to adjust the volume level.
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
  Box,
  Group,
  rem
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
      width={120}
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
          <Group align="center" justify="center">
            <Stack spacing="sm" align="center">
              <Text size="sm" c="amber" fw={500} mb={5}>
                Volume
              </Text>
              <Box h={200}>
                <Slider
                  value={volume}
                  onChange={handleVolumeChange}
                  min={0}
                  max={100}
                  step={1}
                  color="amber"
                  label={(value) => `${value}%`}
                  labelAlwaysOn
                  size="lg"
                  thumbSize={22}
                  orientation="vertical"
                  styles={{
                    track: { height: 180 },
                    thumb: { 
                      borderWidth: 2,
                      borderColor: 'var(--mantine-color-amber-filled)'
                    },
                    markLabel: {
                      fontSize: rem(10)
                    }
                  }}
                  marks={[
                    { value: 0, label: '0%' },
                    { value: 50, label: '50%' },
                    { value: 100, label: '100%' }
                  ]}
                />
              </Box>
              <Text size="sm" ta="center" c="dimmed" mt={5}>
                {volume}%
              </Text>
            </Stack>
          </Group>
        </Box>
      </Menu.Dropdown>
    </Menu>
  );
};

export default VolumeControl;