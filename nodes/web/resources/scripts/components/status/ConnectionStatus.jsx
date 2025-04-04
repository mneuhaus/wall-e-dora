/**
 * ConnectionStatus Component
 * 
 * Displays a status indicator showing whether the WebSocket connection to the server is active.
 * Uses a wifi icon that is green when connected and red when disconnected.
 * 
 * @component
 */
import React from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import { useAppContext } from '../../contexts/AppContext';

const ConnectionStatus = () => {
  const { isConnected } = useAppContext();
  
  return (
    <Tooltip
      label={isConnected ? "Connected to server" : "Disconnected from server"} 
      position="bottom"
      withArrow
    >
      <ActionIcon 
        variant="transparent" 
        radius="xl"
        aria-label="Connection Status"
      >
        <i 
          className="fa-solid fa-wifi" 
          style={{ color: `var(--mantine-color-${isConnected ? 'green' : 'red'}-6)` }}
        ></i>
      </ActionIcon>
    </Tooltip>
  );
};

export default ConnectionStatus;