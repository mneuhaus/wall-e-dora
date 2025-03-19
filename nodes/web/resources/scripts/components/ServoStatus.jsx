import React from 'react';
import { useAppContext } from '../contexts/AppContext';

const ServoStatus = () => {
  const { availableServos } = useAppContext();
  
  return (
    <button className="transparent circle">
      <i className="fa-solid fa-microchip"></i>
      <span className="badge">{availableServos?.length || 0}</span>
    </button>
  );
};

export default ServoStatus;