import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import node from '../Node';

const ServoDebug = () => {
  const { id } = useParams();
  const [servo, setServo] = useState(null);
  const [position, setPosition] = useState(0);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(180);
  
  useEffect(() => {
    // Listen for servo updates
    const unsubscribe = node.on('servo_status', (event) => {
      const servos = event.value || [];
      const servo = servos.find(s => s.id === id);
      if (servo) {
        setServo(servo);
        setPosition(servo.position || 0);
        setMin(servo.min || 0);
        setMax(servo.max || 180);
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, [id]);
  
  const handlePositionChange = (e) => {
    const newPosition = parseInt(e.target.value);
    setPosition(newPosition);
    node.emit('servo_move', [{ id, position: newPosition }]);
  };
  
  const handleCalibrate = () => {
    node.emit('servo_calibrate', [{ id }]);
  };
  
  if (!servo) {
    return (
      <div className="servo-debug">
        <h3>Loading Servo {id}...</h3>
      </div>
    );
  }
  
  return (
    <div className="servo-debug">
      <div className="card large">
        <div className="card-content">
          <span className="card-title">Servo {id} Debug</span>
          
          {servo.description && (
            <p className="servo-description">{servo.description}</p>
          )}
          
          <div className="servo-details">
            <div className="detail-item">
              <span className="label">Current Position:</span>
              <span className="value">{position}°</span>
            </div>
            <div className="detail-item">
              <span className="label">Min Position:</span>
              <span className="value">{min}°</span>
            </div>
            <div className="detail-item">
              <span className="label">Max Position:</span>
              <span className="value">{max}°</span>
            </div>
          </div>
          
          <div className="servo-controls">
            <h5>Position Control</h5>
            <div className="position-slider">
              <input 
                type="range" 
                min={min} 
                max={max} 
                value={position} 
                onChange={handlePositionChange} 
                className="slider" 
              />
              <div className="slider-labels">
                <span>{min}°</span>
                <span>{max}°</span>
              </div>
            </div>
            
            <div className="position-buttons">
              <button 
                onClick={() => handlePositionChange({ target: { value: min } })} 
                className="btn"
              >
                Min
              </button>
              <button 
                onClick={() => handlePositionChange({ target: { value: (min + max) / 2 } })} 
                className="btn"
              >
                Center
              </button>
              <button 
                onClick={() => handlePositionChange({ target: { value: max } })} 
                className="btn"
              >
                Max
              </button>
            </div>
          </div>
          
          <div className="calibration-controls">
            <h5>Calibration</h5>
            <button onClick={handleCalibrate} className="btn">
              Calibrate Servo
            </button>
            <p className="helper-text">
              Calibration will move the servo through its full range to determine min and max positions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServoDebug;