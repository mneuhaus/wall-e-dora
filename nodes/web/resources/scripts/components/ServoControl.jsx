import React, { useState, useEffect } from 'react';
import node from '../Node';
import { useAppContext } from '../contexts/AppContext';
import Slider from 'rc-slider';

const ServoControl = ({ servoId }) => {
  const { availableServos } = useAppContext();
  const [showSettings, setShowSettings] = useState(false);
  const [position, setPosition] = useState(0);
  const [speed, setSpeed] = useState(100);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(180);
  const [servoInfo, setServoInfo] = useState(null);
  
  // Find the servo data from available servos
  useEffect(() => {
    if (availableServos && availableServos.length > 0) {
      const servo = availableServos.find(s => s.id === servoId || s.id === parseInt(servoId));
      if (servo) {
        setServoInfo(servo);
        setPosition(servo.position || 0);
        setSpeed(servo.speed || 100);
        setMin(servo.min_pos || 0);
        setMax(servo.max_pos || 180);
      }
    }
  }, [availableServos, servoId]);
  
  // Listen for servo updates from WebSocket
  useEffect(() => {
    const unsubscribe = node.on('servo_status', (event) => {
      if (event && event.value) {
        const servos = event.value || [];
        const servo = servos.find(s => s.id === servoId || s.id === parseInt(servoId));
        if (servo) {
          setServoInfo(servo);
          setPosition(servo.position || 0);
          setSpeed(servo.speed || 100);
          setMin(servo.min_pos || 0);
          setMax(servo.max_pos || 180);
        }
      }
    });
    
    // Request servo data on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, [servoId]);
  
  const handlePositionUpdate = (newPosition) => {
    const positionValue = parseInt(newPosition);
    setPosition(positionValue);
    node.emit('set_servo', [parseInt(servoId), positionValue, parseInt(speed)]);
  };
  
  const handleSpeedChange = (e) => {
    const newSpeed = parseInt(e.target.value);
    setSpeed(newSpeed);
  };
  
  const updateSpeed = () => {
    node.emit('set_speed', [parseInt(servoId), parseInt(speed)]);
  };
  
  const handleWiggle = () => {
    node.emit('wiggle', [parseInt(servoId)]);
  };
  
  const handleCalibrate = () => {
    node.emit('calibrate', [parseInt(servoId)]);
  };
  
  const servoTitle = servoInfo && servoInfo.alias 
    ? `${servoInfo.alias} (${servoId})` 
    : `Servo ${servoId}`;
  
  // Fallback slider for small screens
  const FallbackSlider = () => (
    <div className="fallback-slider">
      <input 
        type="range" 
        min={min} 
        max={max} 
        value={position} 
        onChange={(e) => handlePositionUpdate(e.target.value)} 
        className="slider" 
      />
      <div className="slider-value">{position}</div>
    </div>
  );
  
  return (
    <div className="servo-control-widget">
      <div className="widget-header">
        <h6 className="title" style={{ color: 'var(--text)' }}>{servoTitle}</h6>
        <div className="flex-spacer"></div>
        <a className="settings-button" onClick={() => setShowSettings(!showSettings)}>
          <i className="fas fa-cog"></i>
        </a>
      </div>
      
      {!showSettings ? (
        <div className="widget-content">
          <div className="control-area">
            <div className="circular-slider-container">
              <div className="position-display">{position}</div>
              <div className="slider-container">
                <Slider
                  value={position}
                  min={min}
                  max={max}
                  onChange={handlePositionUpdate}
                  railStyle={{ backgroundColor: '#37474F', height: 8 }}
                  trackStyle={{ backgroundColor: '#00bfa5', height: 8 }}
                  handleStyle={{
                    borderColor: '#00bfa5',
                    height: 20,
                    width: 20,
                    marginTop: -6,
                    backgroundColor: '#fff',
                    boxShadow: '0 2px 5px rgba(0, 0, 0, 0.3)'
                  }}
                />
              </div>
            </div>
          </div>
          <div className="status-info">
            <div className="info-item">
              <span className="label">Position:</span>
              <span className="value">{position}</span>
            </div>
            <div className="info-item">
              <span className="label">Speed:</span>
              <span className="value">{speed}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="widget-content settings-panel">
          <div className="field label border round m-bottom-2">
            <label className="slider">
              <input 
                type="range" 
                min="100" 
                max="2000" 
                step="10" 
                value={speed}
                onChange={handleSpeedChange}
                onMouseUp={updateSpeed}
                onTouchEnd={updateSpeed}
              />
              <span className="small">Speed: {speed}</span>
            </label>
          </div>
          
          <button className="border full-width m-bottom-2" onClick={handleWiggle}>
            <i className="fas fa-arrows-left-right m-right-1"></i>
            Test Movement
          </button>
          
          <button className="border full-width" onClick={handleCalibrate}>
            <i className="fas fa-ruler m-right-1"></i>
            Calibrate Range
          </button>
        </div>
      )}
    </div>
  );
};

export default ServoControl;