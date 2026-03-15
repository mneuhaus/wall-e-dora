/**
 * EmergencyStopStatus Component
 *
 * Quick-access emergency stop button for halting motion and playing a stop callout.
 *
 * @component
 */
import React from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import { useAppContext } from '../../contexts/AppContext';
import { statusIconStyles } from './StatusIconStyles';

const EmergencyStopStatus = () => {
  const { triggerEmergencyStop } = useAppContext();

  return (
    <Tooltip
      label="Not-Stopp: anhalten und Stopp sagen"
      position="bottom"
      withArrow
    >
      <ActionIcon
        variant="filled"
        radius="xl"
        color="red"
        aria-label="Not-Stopp"
        style={{
          ...statusIconStyles.actionIcon,
          boxShadow: '0 0 0 1px rgba(255, 255, 255, 0.14), 0 8px 18px rgba(0, 0, 0, 0.18)',
        }}
        onClick={triggerEmergencyStop}
      >
        <i
          className="fa-solid fa-hand"
          style={{
            color: '#fff',
            ...statusIconStyles.icon,
          }}
        ></i>
      </ActionIcon>
    </Tooltip>
  );
};

export default EmergencyStopStatus;
