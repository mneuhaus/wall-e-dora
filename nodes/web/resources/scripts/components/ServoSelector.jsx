import React, { useState, useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';

const ServoSelector = ({ value, onChange, label }) => {
  const { availableServos } = useAppContext();
  const [isOpen, setIsOpen] = useState(false);
  const [selectedServo, setSelectedServo] = useState(null);

  // Find the selected servo info from available servos when value changes
  useEffect(() => {
    if (availableServos && availableServos.length > 0 && value) {
      const selectedId = parseInt(value);
      const servo = availableServos.find(s => {
        const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
        return currentId === selectedId;
      });
      
      if (servo) {
        setSelectedServo(servo);
      }
    }
  }, [availableServos, value]);

  const handleSelectServo = (servoId) => {
    onChange(servoId);
    setIsOpen(false);
  };

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="servo-selector">
      <label className="servo-selector-label">{label || 'Select Servo'}</label>
      <button 
        className="servo-selector-button" 
        onClick={toggleDropdown}
      >
        {selectedServo ? `Servo ${selectedServo.id}` : 'None Selected'}
        <i className={`fas fa-chevron-${isOpen ? 'up' : 'down'}`}></i>
      </button>
      
      {isOpen && (
        <div className="servo-selector-dropdown">
          <div className="servo-selector-option" onClick={() => handleSelectServo(null)}>
            <div className="servo-option-text">None</div>
          </div>
          {availableServos && availableServos.map((servo) => (
            <div 
              key={servo.id} 
              className={`servo-selector-option ${parseInt(value) === parseInt(servo.id) ? 'selected' : ''}`} 
              onClick={() => handleSelectServo(servo.id)}
            >
              <div className="servo-option-text">
                Servo {servo.id}
                {servo.name && <span className="servo-name"> ({servo.name})</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ServoSelector;