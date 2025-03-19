import React, { useState, useEffect } from 'react';
import node from '../Node';

const ServoControl = ({ servoId }) => {
  const [position, setPosition] = useState(0);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(180);
  const [servoInfo, setServoInfo] = useState(null);
  
  useEffect(() => {
    // Listen for servo updates
    const unsubscribe = node.on('servo_status', (event) => {
      const servos = event.value || [];
      const servo = servos.find(s => s.id === servoId);
      if (servo) {
        setServoInfo(servo);
        setPosition(servo.position || 0);
        setMin(servo.min || 0);
        setMax(servo.max || 180);
      }
    });
    
    return unsubscribe;
  }, [servoId]);
  
  const handlePositionChange = (e) => {
    const newPosition = parseInt(e.target.value);
    setPosition(newPosition);
    node.emit('servo_move', [{ id: servoId, position: newPosition }]);
  };
  
  return (
    <div className="servo-control">
      <div className="servo-info">
        <h5>Servo {servoId}</h5>
        {servoInfo && servoInfo.description && (
          <p>{servoInfo.description}</p>
        )}
      </div>
      
      <div className="servo-slider">
        <label>Position: {position}°</label>
        <input 
          type="range" 
          min={min} 
          max={max} 
          value={position} 
          onChange={handlePositionChange} 
          className="slider" 
        />
      </div>
      
      <div className="servo-buttons">
        <button 
          onClick={() => handlePositionChange({ target: { value: min } })} 
          className="btn-small"
        >
          Min
        </button>
        <button 
          onClick={() => handlePositionChange({ target: { value: (min + max) / 2 } })} 
          className="btn-small"
        >
          Center
        </button>
        <button 
          onClick={() => handlePositionChange({ target: { value: max } })} 
          className="btn-small"
        >
          Max
        </button>
      </div>
    </div>
  );
};

export default ServoControl;