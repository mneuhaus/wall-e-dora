import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import node from '../Node';
import Slider from 'rc-slider';

const ServoDebug = () => {
  const { id } = useParams();
  const [servo, setServo] = useState(null);
  const [position, setPosition] = useState(0);
  const [speed, setSpeed] = useState(100);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(180);
  const [newId, setNewId] = useState('');
  const [aliasInput, setAliasInput] = useState('');
  
  useEffect(() => {
    // Listen for servo updates
    const unsubscribe = node.on('servo_status', (event) => {
      const servos = event.value || [];
      const servo = servos.find(s => s.id === parseInt(id));
      if (servo) {
        setServo(servo);
        setPosition(servo.position || 0);
        setSpeed(servo.speed || 100);
        setMin(servo.min_pos || 0);
        setMax(servo.max_pos || 180);
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, [id]);
  
  const handlePositionUpdate = (newPosition) => {
    setPosition(newPosition);
    node.emit('set_servo', [parseInt(id), newPosition, parseInt(speed)]);
  };
  
  const handleSpeedChange = (e) => {
    const newSpeed = parseInt(e.target.value);
    setSpeed(newSpeed);
    node.emit('set_speed', [parseInt(id), newSpeed]);
  };
  
  const handleWiggle = () => {
    node.emit('wiggle', [parseInt(id)]);
  };
  
  const handleCalibrate = () => {
    node.emit('calibrate', [parseInt(id)]);
  };
  
  const handleChangeId = () => {
    if (newId.trim() !== '') {
      node.emit('change_servo_id', [parseInt(id), parseInt(newId)]);
    }
  };
  
  const handleSetAlias = () => {
    if (aliasInput.trim() !== '') {
      node.emit('set_alias', [parseInt(id), aliasInput.trim()]);
      setAliasInput(''); // Clear input after sending
    }
  };
  
  const servoStatus = servo ? {
    Position: servo.position || 'N/A',
    Speed: servo.speed || 'N/A',
    Torque: servo.torque || 'N/A',
    Alias: servo.alias || 'None'
  } : {};
  
  if (!servo) {
    return (
      <div className="servo-debug">
        <article className="responsive">
          <header className="m-bottom-2">
            <h5>Loading Servo {id}...</h5>
          </header>
        </article>
      </div>
    );
  }
  
  return (
    <div className="servo-debug">
      <article className="responsive">
        {/* Header Section with Breadcrumb */}
        <header className="m-bottom-2">
          <nav aria-label="breadcrumb">
            <Link to="/" className="small">Home</Link>
            <span className="small">/</span>
            <span className="small" aria-current="page">Servo {id}</span>
          </nav>
          <h5 className="m-top-1">Servo Control Panel</h5>
          <p className="small text-gray">Configure and monitor servo behavior</p>
        </header>

        <div className="grid gap-2">
          {/* Left Column: Position Control */}
          <div className="s12 m6 l4">
            <section className="card p-3">
              <h6 className="m-bottom-2">Position Control</h6>
              <div className="center-align" role="group" aria-label="Position control">
                <div className="circular-slider-container">
                  <div className="position-display">{position}</div>
                  <div className="slider-container">
                    <Slider
                      value={position}
                      min={min}
                      max={max}
                      onChange={handlePositionUpdate}
                      railStyle={{ backgroundColor: '#37474F', height: 10 }}
                      trackStyle={{ backgroundColor: '#00bfa5', height: 10 }}
                      handleStyle={{
                        borderColor: '#00bfa5',
                        height: 24,
                        width: 24,
                        marginTop: -7,
                        backgroundColor: '#fff',
                        boxShadow: '0 2px 5px rgba(0, 0, 0, 0.3)'
                      }}
                      aria-label="Servo position control"
                    />
                  </div>
                </div>
                <div className="field label border round m-top-2">
                  <label className="slider">
                    <input 
                      type="range" 
                      min="100" 
                      max="2000" 
                      step="1" 
                      value={speed}
                      onChange={handleSpeedChange}
                      aria-label="Servo speed control"
                    />
                    <span className="small">Speed: {speed}</span>
                  </label>
                </div>
              </div>
            </section>
          </div>

          {/* Middle Column: Status and Calibration */}
          <div className="s12 m6 l4">
            <section className="card p-3 m-bottom-2">
              <h6 className="m-bottom-2">Current Status</h6>
              <div className="status-grid">
                {Object.entries(servoStatus).map(([key, value]) => (
                  <div key={key} className="status-item p-1">
                    <span className="label text-gray">{key}</span>
                    <span className="value">{value}</span>
                  </div>
                ))}
              </div>
            </section>

            {servo.min_pos !== undefined && (
              <section className="card p-3">
                <h6 className="m-bottom-2">Calibration Range</h6>
                <div className="status-grid">
                  <div className="status-item p-1">
                    <span className="label text-gray">Min Position</span>
                    <span className="value">{servo.min_pos || 'Not calibrated'}</span>
                  </div>
                  <div className="status-item p-1">
                    <span className="label text-gray">Max Position</span>
                    <span className="value">{servo.max_pos || 'Not calibrated'}</span>
                  </div>
                </div>
              </section>
            )}
          </div>

          {/* Right Column: Controls */}
          <div className="s12 m12 l4">
            <section className="card p-3">
              <h6 className="m-bottom-2">Servo Configuration</h6>
              
              <div className="field label round m-bottom-2" style={{ display: 'flex' }}>
                <input 
                  className="border"
                  type="number" 
                  value={newId}
                  onChange={(e) => setNewId(e.target.value)}
                  aria-label="New servo ID"
                  min="1"
                  max="253"
                />
                <label>New Servo ID</label>
                <button 
                  onClick={handleChangeId}
                  disabled={!newId}
                  aria-label="Change servo ID"
                >
                  Change ID
                </button>
              </div>

              <div className="field label round m-bottom-2" style={{ display: 'flex' }}>
                <input 
                  className="border"
                  type="text" 
                  value={aliasInput}
                  onChange={(e) => setAliasInput(e.target.value)}
                  aria-label="Servo alias"
                  placeholder="Enter alias"
                />
                <label>Servo Alias</label>
                <button 
                  onClick={handleSetAlias}
                  disabled={!aliasInput}
                  aria-label="Set alias"
                >
                  Set Alias
                </button>
              </div>

              <div className="actions m-top-2">
                <button 
                  className="border m-right-2 p-2"
                  onClick={handleWiggle}
                  aria-label="Test servo movement"
                >
                  <i className="fa-solid fa-arrows-left-right m-right-1"></i>
                  Test Movement
                </button>
                <button 
                  className="border p-2"
                  onClick={handleCalibrate}
                  aria-label="Calibrate servo range"
                >
                  <i className="fa-solid fa-ruler m-right-1"></i>
                  Calibrate Range
                </button>
              </div>
            </section>
          </div>
        </div>
      </article>
    </div>
  );
};

export default ServoDebug;