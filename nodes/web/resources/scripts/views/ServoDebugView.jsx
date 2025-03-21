/**
 * ServoDebugView Component
 * 
 * Provides a detailed interface for debugging and configuring a single servo.
 * Includes position control, speed settings, calibration, and configuration options.
 * 
 * @component
 */
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import node from '../Node';
import Slider from 'rc-slider';

const ServoDebugView = () => {
  const { id } = useParams();
  const [servo, setServo] = useState(null);
  const [position, setPosition] = useState(0);
  const [speed, setSpeed] = useState(100);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(1024);
  const [newId, setNewId] = useState('');
  const [aliasInput, setAliasInput] = useState('');
  const [attachIndex, setAttachIndex] = useState("");
  const [isCalibrating, setIsCalibrating] = useState(false);
  
  useEffect(() => {
    // Listen for servo updates
    const unsubscribe = node.on('servo_status', (event) => {
      const servos = event.value || [];
      const servo = servos.find(s => s.id === parseInt(id));
      if (servo) {
        setServo(servo);
        
        // Get range from servo
        const servoMinPos = servo.min_pos || 0;
        const servoMaxPos = servo.max_pos || 4095;
        setMin(servoMinPos);
        setMax(servoMaxPos);
        
        // Get current servo position
        const servoPosition = servo.position || 0;
        
        // Map servo position (min-max) to UI range (0-300)
        const uiPosition = Math.round(
          300 * (servoPosition - servoMinPos) / (servoMaxPos - servoMinPos)
        );
        
        setPosition(uiPosition);
        setSpeed(servo.speed || 100);
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, [id]);
  
  const handlePositionChange = (newPosition) => {
    // Ensure we have a valid number
    const positionValue = parseInt(newPosition);
    
    if (!isNaN(positionValue)) {
      // Update the local state immediately for responsive UI
      setPosition(positionValue);
      
      // Map UI slider value (0-300) to servo range (min-max)
      let servoMinPos = min || 0;
      let servoMaxPos = max || 4095;
      
      // Linear mapping from UI range (0-300) to servo range
      const servoPosition = Math.round(
        servoMinPos + (positionValue / 300) * (servoMaxPos - servoMinPos)
      );
      
      // Use stronger debounce to limit servo commands
      clearTimeout(window.servoUpdateTimeout);
      window.servoUpdateTimeout = setTimeout(() => {
        node.emit('set_servo', [parseInt(id), servoPosition]);
      }, 300); // 300ms debounce for smoother experience
    }
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
    setIsCalibrating(true);
    node.emit('calibrate', [parseInt(id)]);
    
    // Auto-disable calibration mode after 3 seconds
    setTimeout(() => {
      setIsCalibrating(false);
    }, 3000);
  };
  
  const handleChangeId = () => {
    if (newId.trim() !== '') {
      node.emit('change_servo_id', [parseInt(id), parseInt(newId)]);
      setNewId(''); // Clear input after sending
    }
  };
  
  const handleSetAlias = () => {
    if (aliasInput.trim() !== '') {
      node.emit('set_alias', [parseInt(id), aliasInput.trim()]);
      setAliasInput(''); // Clear input after sending
    }
  };
        
  const handleAttachServo = () => {
    if (attachIndex) {
      node.emit('attach_servo', [parseInt(id), attachIndex]);
      
      // Show toast notification instead of alert
      const toast = document.createElement('aside');
      toast.className = 'toast top-right success';
      toast.innerHTML = `<div>${attachIndex} attached to Servo ${id}</div>`;
      document.body.appendChild(toast);
      
      // Clean up toast after animation
      setTimeout(() => {
        document.body.removeChild(toast);
      }, 3000);
    }
  };
        
  const handleResetServo = () => {
    if (window.confirm('Are you sure you want to reset this servo to factory defaults? This will remove all calibration settings and aliases.')) {
      node.emit('reset_servo', [parseInt(id)]);
    }
  };
  
  const servoStatus = servo ? {
    Position: servo.position || 'N/A',
    Speed: servo.speed || 'N/A',
    Alias: servo.alias || 'None'
  } : {};
  
  if (!servo) {
    return (
      <div className="servo-debug">
        <article className="responsive">
          <header>
            <nav>
              <Link to="/" className="circle icon"><i className="fa-solid fa-arrow-left"></i></Link>
              <h5>Loading Servo Data...</h5>
            </nav>
          </header>
          <div className="center-align large-space">
            <div className="loader medium"></div>
            <p className="text-secondary">Connecting to Servo {id}</p>
          </div>
        </article>
      </div>
    );
  }
  
  return (
    <div className="servo-debug">
      <article className="responsive">
        {/* Header Section */}
        <header>
          <nav>
            <Link to="/" className="circle icon"><i className="fa-solid fa-arrow-left"></i></Link>
            <h5>Servo {id}{servo.alias ? `: ${servo.alias}` : ''}</h5>
          </nav>
        </header>
        
        <div className="grid">
          {/* Position Control Section */}
          <div className="s12 m6 l4">
            <section className="card servo-control-card">
              <header>
                <h5 className="amber-text">Position Control</h5>
              </header>
              <div>
                <div className="position-display center-align">
                  <div className="large">{position}°</div>
                  <div className="small text-secondary">Servo Angle</div>
                </div>
                
                <div className="field">
                  <Slider
                    min={0}
                    max={300}
                    value={position}
                    onChange={handlePositionChange}
                    railStyle={{ backgroundColor: "rgba(55, 71, 79, 0.3)" }}
                    trackStyle={{ backgroundColor: "var(--primary)" }}
                    handleStyle={{ borderColor: "var(--primary)" }}
                  />
                  <span className="helper">Min: 0° | Max: 300°</span>
                </div>
              </div>
              
              <div className="field">
                <label>Speed Control</label>
                <input
                  type="range"
                  min="100"
                  max="2000"
                  step="1"
                  value={speed}
                  onChange={handleSpeedChange}
                  className="amber"
                />
                <span className="helper">Current Speed: {speed}</span>
              </div>
              
              <div className="field buttons">
                <button 
                  className="border round"
                  onClick={handleWiggle}
                  aria-label="Test servo movement"
                >
                  <i className="fa-solid fa-arrows-left-right left"></i>
                  Test Motion
                </button>
                <button 
                  className={`border round ${isCalibrating ? 'amber' : ''}`}
                  onClick={handleCalibrate}
                  aria-label="Calibrate servo range"
                >
                  <i className="fa-solid fa-ruler left"></i>
                  Calibrate
                </button>
              </div>
            </section>
          </div>

          {/* Status & Calibration Section */}
          <div className="s12 m6 l4">
            <section className="card servo-status-card">
              <header>
                <h5 className="amber-text">Servo Status</h5>
              </header>
              
              <div>
                <ul className="list">
                  {Object.entries(servoStatus).map(([key, value]) => (
                    <li key={key} className="border-bottom">
                      <div className="grid">
                        <div className="s6 text-secondary">{key}</div>
                        <div className="s6 text-right amber-text">{value}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </section>
            
            {servo.min_pos !== undefined && (
              <section className="card calibration-card mt-4">
                <header>
                  <h5 className="amber-text">Calibration Range</h5>
                </header>
                
                <div>
                  <ul className="list">
                    <li className="border-bottom">
                      <div className="grid">
                        <div className="s6 text-secondary">Min Position</div>
                        <div className="s6 text-right amber-text">{servo.min_pos || 'Not calibrated'}</div>
                      </div>
                    </li>
                    <li className="border-bottom">
                      <div className="grid">
                        <div className="s6 text-secondary">Max Position</div>
                        <div className="s6 text-right amber-text">{servo.max_pos || 'Not calibrated'}</div>
                      </div>
                    </li>
                  </ul>
                </div>
              </section>
            )}
          </div>

          {/* Configuration Section */}
          <div className="s12 m12 l4">
            <section className="card config-card">
              <header>
                <h5 className="amber-text">Servo Configuration</h5>
              </header>
              
              <div>
                <div className="field label border round">
                  <input
                    type="number"
                    value={newId}
                    onChange={(e) => setNewId(e.target.value)}
                    min="1"
                    max="253"
                    required
                  />
                  <label>New Servo ID</label>
                  <button 
                    className="round border"
                    onClick={handleChangeId}
                    disabled={!newId}
                  >
                    Update
                  </button>
                </div>
              </div>
              
              <div>
                <div className="field label border round">
                  <input
                    type="text"
                    value={aliasInput}
                    onChange={(e) => setAliasInput(e.target.value)}
                    required
                  />
                  <label>Servo Alias</label>
                  <button 
                    className="round border"
                    onClick={handleSetAlias}
                    disabled={!aliasInput}
                  >
                    Set
                  </button>
                </div>
              </div>
              
              <div>
                <div className="field label border">
                  <select 
                    value={attachIndex} 
                    onChange={(e) => setAttachIndex(e.target.value)}
                    required
                  >
                    <option value="" disabled>Choose a control</option>
                    <optgroup label="Buttons">
                      <option value="FACE_1">FACE_1</option>
                      <option value="FACE_2">FACE_2</option>
                      <option value="FACE_3">FACE_3</option>
                      <option value="FACE_4">FACE_4</option>
                      <option value="LEFT_SHOULDER">LEFT_SHOULDER</option>
                      <option value="RIGHT_SHOULDER">RIGHT_SHOULDER</option>
                      <option value="LEFT_SHOULDER_BOTTOM">LEFT_SHOULDER_BOTTOM</option>
                      <option value="RIGHT_SHOULDER_BOTTOM">RIGHT_SHOULDER_BOTTOM</option>
                      <option value="SELECT">SELECT</option>
                      <option value="START">START</option>
                      <option value="LEFT_ANALOG_BUTTON">LEFT_ANALOG_BUTTON</option>
                      <option value="RIGHT_ANALOG_BUTTON">RIGHT_ANALOG_BUTTON</option>
                      <option value="DPAD_UP">DPAD_UP</option>
                      <option value="DPAD_DOWN">DPAD_DOWN</option>
                      <option value="DPAD_LEFT">DPAD_LEFT</option>
                      <option value="DPAD_RIGHT">DPAD_RIGHT</option>
                      <option value="HOME">HOME</option>
                      <option value="MISCBUTTON_1">MISCBUTTON_1</option>
                      <option value="MISCBUTTON_2">MISCBUTTON_2</option>
                    </optgroup>
                    <optgroup label="Axes">
                      <option value="LEFT_ANALOG_STICK_X">LEFT_ANALOG_STICK_X</option>
                      <option value="LEFT_ANALOG_STICK_Y">LEFT_ANALOG_STICK_Y</option>
                      <option value="RIGHT_ANALOG_STICK_X">RIGHT_ANALOG_STICK_X</option>
                      <option value="RIGHT_ANALOG_STICK_Y">RIGHT_ANALOG_STICK_Y</option>
                    </optgroup>
                  </select>
                  <label>Gamepad Control</label>
                  <button 
                    className="round border amber"
                    onClick={handleAttachServo}
                    disabled={!attachIndex}
                  >
                    <i className="fa-solid fa-gamepad left"></i>
                    Attach
                  </button>
                </div>
              </div>
              
              <div className="divider"></div>
              
              <div className="danger-zone">
                <button 
                  className="border round error full-width"
                  onClick={handleResetServo}
                >
                  <i className="fa-solid fa-rotate-left left"></i>
                  Reset to Factory Defaults
                </button>
              </div>
            </section>
          </div>
        </div>
      </article>
    </div>
  );
};

export default ServoDebugView;