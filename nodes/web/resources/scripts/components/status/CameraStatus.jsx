/**
 * CameraStatus Component
 *
 * Toggles the full-screen camera background behind the UI.
 *
 * @component
 */
import React from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import { useAppContext } from '../../contexts/AppContext';
import { statusIconStyles } from './StatusIconStyles';

const CameraStatus = () => {
  const { cameraBackgroundEnabled, toggleCameraBackground } = useAppContext();

  return (
    <Tooltip
      label={cameraBackgroundEnabled ? 'Kamerahintergrund ausblenden' : 'Kamerahintergrund einblenden'}
      position="bottom"
      withArrow
    >
      <ActionIcon
        variant="transparent"
        radius="xl"
        aria-label="Kamerahintergrund"
        style={statusIconStyles.actionIcon}
        onClick={toggleCameraBackground}
      >
        <i
          className="fa-solid fa-camera"
          style={{
            color: cameraBackgroundEnabled
              ? 'var(--mantine-color-amber-5)'
              : 'var(--mantine-color-gray-6)',
            ...statusIconStyles.icon,
          }}
        ></i>
      </ActionIcon>
    </Tooltip>
  );
};

export default CameraStatus;
