import React from 'react';
import { useAppContext } from '../contexts/AppContext';

const ConnectionStatus = () => {
  const { isConnected } = useAppContext();
  
  return (
    <button className={`transparent circle ${isConnected ? 'green' : 'red'}`}>
      <i className="fa-solid fa-wifi"></i>
    </button>
  );
};

export default ConnectionStatus;