import React from 'react';
import { useGridContext } from '../contexts/GridContext';

const GridLock = () => {
  const { isEditable, toggleGridEditing, resetGridLayout } = useGridContext();
  
  const handleResetGrid = (e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to reset the grid layout? This will clear all widgets for all devices.')) {
      resetGridLayout();
      console.log('Grid layout reset globally. All devices will be affected.');
    }
  };
  
  return (
    <div className="grid-lock-container" style={{ display: 'flex', gap: '10px' }}>
      <button 
        onClick={toggleGridEditing} 
        className={`transparent circle ${isEditable ? 'green' : 'amber'}`}
        title={isEditable ? "Lock grid (exit edit mode)" : "Unlock grid (enter edit mode)"}
      >
        <i className={`fa-solid ${isEditable ? 'fa-lock-open' : 'fa-lock'}`}></i>
      </button>
      
      {isEditable && (
        <button 
          onClick={handleResetGrid} 
          className="transparent circle red"
          title="Reset grid layout for all devices"
        >
          <i className="fa-solid fa-trash"></i>
        </button>
      )}
    </div>
  );
};

export default GridLock;