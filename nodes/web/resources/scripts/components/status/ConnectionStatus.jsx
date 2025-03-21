/**
 * ConnectionStatus Component
 * 
 * Displays a status indicator showing whether the WebSocket connection to the server is active.
 * Uses a wifi icon that is green when connected and red when disconnected.
 * 
 * @component
 */
import React from 'react';
import { useAppContext } from '../../contexts/AppContext';

const ConnectionStatus = () => {
  const { isConnected } = useAppContext();
  
  return (
    <button 
      className="transparent circle"
      aria-label="Connection Status"
    >
      <i className={`fa-solid fa-wifi ${isConnected ? 'green-text' : 'red-text'}`}></i>
    </button>
  );
};

export default ConnectionStatus;