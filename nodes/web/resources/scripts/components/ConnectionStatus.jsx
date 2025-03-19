import React from 'react';
import { useAppContext } from '../contexts/AppContext';

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