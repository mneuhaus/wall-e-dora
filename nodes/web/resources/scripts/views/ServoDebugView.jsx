/**
 * ServoDebugView Component
 * 
 * A comprehensive interface for debugging and configuring a single servo.
 * Provides intuitive controls for position, speed, calibration, and advanced configuration.
 * 
 * Features:
 * - Visual circular position control
 * - Real-time status monitoring
 * - Servo calibration tools
 * - Gamepad control mapping
 * - Configuration management
 * 
 * @component
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import node from '../Node';
import Slider from 'rc-slider';
import CircularSlider from 'react-circular-slider-svg';

const ServoDebugView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [servo, setServo] = useState(null);
  const [position, setPosition] = useState(0);
  const [displayPosition, setDisplayPosition] = useState(0); // For UI display (0-300 degrees)
  const [speed, setSpeed] = useState(100);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(4095);
  const [activeTab, setActiveTab] = useState('control');
  const [newId, setNewId] = useState('');
  const [aliasInput, setAliasInput] = useState('');
  const [attachIndex, setAttachIndex] = useState("");
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [showAdvancedControls, setShowAdvancedControls] = useState(false);
  const [isToastVisible, setIsToastVisible] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState('success');
  const positionUpdateTimeout = useRef(null);
  
  // Tabs configuration for better organization
  const tabs = [
    { id: 'control', label: 'Control', icon: 'fa-sliders-h' },
    { id: 'settings', label: 'Settings', icon: 'fa-cog' },
    { id: 'gamepad', label: 'Gamepad', icon: 'fa-gamepad' },
    { id: 'info', label: 'Info', icon: 'fa-info-circle' }
  ];

  // Function to show toast notifications
  const showToast = (message, type = 'success') => {
    setToastMessage(message);
    setToastType(type);
    setIsToastVisible(true);
    
    setTimeout(() => {
      setIsToastVisible(false);
    }, 3000);
  };
  
  // Helper function to map servo position to UI angle (0-300 degrees)
  const mapServoToUI = useCallback((servoPos, servoMin, servoMax) => {
    return Math.round(300 * (servoPos - servoMin) / (servoMax - servoMin));
  }, []);
  
  // Helper function to map UI angle to servo position
  const mapUIToServo = useCallback((uiPos, servoMin, servoMax) => {
    return Math.round(servoMin + (uiPos / 300) * (servoMax - servoMin));
  }, []);

  useEffect(() => {
    // Listen for servo updates
    const unsubscribe = node.on('servo_status', (event) => {
      const servos = event.value || [];
      const currentServo = servos.find(s => s.id === parseInt(id));
      
      if (currentServo) {
        setServo(currentServo);
        
        // Get range from servo
        const servoMinPos = currentServo.min_pos !== undefined ? currentServo.min_pos : 0;
        const servoMaxPos = currentServo.max_pos !== undefined ? currentServo.max_pos : 4095;
        setMin(servoMinPos);
        setMax(servoMaxPos);
        
        // Get current servo position
        const servoPosition = currentServo.position || 0;
        
        // Set raw position value
        setPosition(servoPosition);
        
        // Map servo position to UI range (0-300 degrees)
        const uiPosition = mapServoToUI(servoPosition, servoMinPos, servoMaxPos);
        setDisplayPosition(uiPosition);
        
        // Set speed
        setSpeed(currentServo.speed || 100);
        
        // Update alias input if it's empty and the servo has an alias
        if (aliasInput === '' && currentServo.alias) {
          setAliasInput(currentServo.alias);
        }
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, [id, mapServoToUI, aliasInput]);
  
  const handlePositionChange = (newPosition) => {
    // Update display position immediately for responsive UI
    setDisplayPosition(newPosition);
    
    // Map UI range (0-300) to servo range (min-max)
    const servoPosition = mapUIToServo(newPosition, min, max);
    setPosition(servoPosition);
    
    // Debounce servo commands
    clearTimeout(positionUpdateTimeout.current);
    positionUpdateTimeout.current = setTimeout(() => {
      node.emit('set_servo', [parseInt(id), servoPosition, speed]);
    }, 50);
  };
  
  const handleSpeedChange = (newSpeed) => {
    setSpeed(newSpeed);
    node.emit('set_speed', [parseInt(id), newSpeed]);
    showToast(`Speed set to ${newSpeed}`);
  };
  
  const handleWiggle = () => {
    setIsTesting(true);
    node.emit('wiggle', [parseInt(id)]);
    showToast('Testing servo motion...');
    
    // Auto-disable testing mode after 3 seconds
    setTimeout(() => {
      setIsTesting(false);
    }, 3000);
  };
  
  const handleCalibrate = () => {
    setIsCalibrating(true);
    node.emit('calibrate', [parseInt(id)]);
    showToast('Calibrating servo range...', 'info');
    
    // Auto-disable calibration mode after 3 seconds
    setTimeout(() => {
      setIsCalibrating(false);
      showToast('Calibration complete!');
    }, 3000);
  };
  
  const handleChangeId = () => {
    if (newId.trim() === '') return;
    
    const newIdInt = parseInt(newId);
    if (isNaN(newIdInt) || newIdInt < 1 || newIdInt > 253) {
      showToast('ID must be between 1 and 253', 'error');
      return;
    }
    
    // Confirm before changing ID
    if (window.confirm(`Are you sure you want to change the servo ID from ${id} to ${newId}? You'll be redirected to the new servo page.`)) {
      node.emit('change_servo_id', [parseInt(id), newIdInt]);
      setNewId('');
      showToast(`Changing servo ID to ${newId}...`);
      
      // Navigate to the new servo page after a short delay
      setTimeout(() => {
        navigate(`/servo/${newId}`);
      }, 1500);
    }
  };
  
  const handleSetAlias = () => {
    if (aliasInput.trim() === '') return;
    
    node.emit('set_alias', [parseInt(id), aliasInput.trim()]);
    showToast(`Alias set to "${aliasInput}"`);
  };
  
  const handleAttachServo = () => {
    if (!attachIndex) return;
    
    node.emit('attach_servo', [parseInt(id), attachIndex]);
    showToast(`Attached to gamepad control: ${attachIndex}`);
  };
  
  const handleResetServo = () => {
    if (window.confirm('Are you sure you want to reset this servo to factory defaults? This will remove all calibration settings and aliases.')) {
      node.emit('reset_servo', [parseInt(id)]);
      showToast('Servo reset to factory defaults', 'info');
    }
  };
  
  const loadingView = (
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
  
  if (!servo) {
    return loadingView;
  }
  
  const servoStatus = {
    Position: position || 'N/A',
    Speed: speed || 'N/A',
    Alias: servo.alias || 'None',
    'Min Position': servo.min_pos !== undefined ? servo.min_pos : 'Not calibrated',
    'Max Position': servo.max_pos !== undefined ? servo.max_pos : 'Not calibrated',
    'Attached Control': servo.attached_control || 'None'
  };
  
  return (
    <div className="servo-debug">
      {/* Toast notification */}
      {isToastVisible && (
        <div className={`toast top-right ${toastType}`}>
          <div>{toastMessage}</div>
        </div>
      )}
      
      <article className="responsive">
        {/* Header Section */}
        <header>
          <nav>
            <Link to="/" className="circle icon"><i className="fa-solid fa-arrow-left"></i></Link>
            <h5>
              Servo {id}
              {servo.alias ? `: ${servo.alias}` : ''}
            </h5>
          </nav>
        </header>
        
        {/* Tabs navigation */}
        <div className="tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab-button ${activeTab === tab.id ? 'active amber' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <i className={`fa-solid ${tab.icon}`}></i>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
        
        <div className="tab-content">
          {/* Control Tab */}
          {activeTab === 'control' && (
            <div className="tab-panel">
              <div className="card">
                <header>
                  <h5 className="amber-text">Position Control</h5>
                </header>
                
                <div className="circular-slider-container">
                  <CircularSlider
                    size={250}
                    minValue={0}
                    maxValue={300}
                    startAngle={0}
                    endAngle={300}
                    handleSize={18}
                    handle1={{
                      value: displayPosition,
                      onChange: handlePositionChange
                    }}
                    arcColor="#222"
                    arcBackgroundColor="rgba(0, 0, 0, 0.2)"
                    coerceToInt={true}
                    handleColor="var(--primary)"
                    labelColor="var(--primary)"
                    labelFontSize="1.2rem"
                    data={[]}
                    label="Position"
                  />
                  
                  <div className="position-display center-align">
                    <div className="large">{displayPosition}°</div>
                    <div className="small text-secondary">Servo Angle</div>
                  </div>
                </div>
                
                {/* Fallback linear slider for more precise control */}
                <div className="field">
                  <Slider
                    min={0}
                    max={300}
                    value={displayPosition}
                    onChange={handlePositionChange}
                    railStyle={{ backgroundColor: "rgba(55, 71, 79, 0.3)" }}
                    trackStyle={{ backgroundColor: "var(--primary)" }}
                    handleStyle={{ borderColor: "var(--primary)" }}
                  />
                  <span className="helper">Range: 0° - 300°</span>
                </div>
                
                <div className="field">
                  <label>
                    Speed Control
                    <span className="small badge right amber">{speed}</span>
                  </label>
                  <input
                    type="range"
                    min="50"
                    max="2000"
                    step="10"
                    value={speed}
                    onChange={(e) => handleSpeedChange(parseInt(e.target.value))}
                    className="amber"
                  />
                  <span className="helper">Lower values = faster movement</span>
                </div>
                
                <div className="actions">
                  <button 
                    className={`border round ${isTesting ? 'amber' : ''}`}
                    onClick={handleWiggle}
                    disabled={isTesting}
                  >
                    <i className="fa-solid fa-arrows-left-right left"></i>
                    Test Motion
                  </button>
                  <button 
                    className={`border round ${isCalibrating ? 'amber' : ''}`}
                    onClick={handleCalibrate}
                    disabled={isCalibrating}
                  >
                    <i className="fa-solid fa-ruler left"></i>
                    Calibrate
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="tab-panel">
              <div className="card">
                <header>
                  <h5 className="amber-text">Servo Configuration</h5>
                  <button 
                    className="small border round right"
                    onClick={() => setShowAdvancedControls(!showAdvancedControls)}
                  >
                    {showAdvancedControls ? 'Hide Advanced' : 'Show Advanced'}
                  </button>
                </header>
                
                <div className="field label border round">
                  <input
                    type="text"
                    value={aliasInput}
                    onChange={(e) => setAliasInput(e.target.value)}
                    placeholder="Friendly name for this servo"
                    maxLength={20}
                  />
                  <label>Servo Alias</label>
                  <button 
                    className="round border amber"
                    onClick={handleSetAlias}
                    disabled={!aliasInput.trim()}
                  >
                    <i className="fa-solid fa-tag left"></i>
                    Set
                  </button>
                </div>
                
                {showAdvancedControls && (
                  <div className="advanced-settings">
                    <div className="field label border round">
                      <input
                        type="number"
                        value={newId}
                        onChange={(e) => setNewId(e.target.value)}
                        min="1"
                        max="253"
                        placeholder="New ID (1-253)"
                      />
                      <label>Change Servo ID</label>
                      <button 
                        className="round border"
                        onClick={handleChangeId}
                        disabled={!newId}
                      >
                        <i className="fa-solid fa-id-card left"></i>
                        Update
                      </button>
                    </div>
                    
                    <div className="danger-zone">
                      <div className="text-error center-align small mb-2">
                        <i className="fa-solid fa-exclamation-triangle"></i> 
                        Danger Zone
                      </div>
                      <button 
                        className="border round error full-width"
                        onClick={handleResetServo}
                      >
                        <i className="fa-solid fa-rotate-left left"></i>
                        Reset to Factory Defaults
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Gamepad Tab */}
          {activeTab === 'gamepad' && (
            <div className="tab-panel">
              <div className="card">
                <header>
                  <h5 className="amber-text">Gamepad Mapping</h5>
                </header>
                
                <div className="field">
                  <p className="small mb-2">Map this servo to a gamepad control for remote operation</p>
                  
                  <div className="field label border">
                    <select 
                      value={attachIndex} 
                      onChange={(e) => setAttachIndex(e.target.value)}
                    >
                      <option value="" disabled>Choose a control</option>
                      <optgroup label="Buttons">
                        <option value="FACE_1">FACE_1 (A/Cross)</option>
                        <option value="FACE_2">FACE_2 (B/Circle)</option>
                        <option value="FACE_3">FACE_3 (X/Square)</option>
                        <option value="FACE_4">FACE_4 (Y/Triangle)</option>
                        <option value="LEFT_SHOULDER">LEFT_SHOULDER (LB)</option>
                        <option value="RIGHT_SHOULDER">RIGHT_SHOULDER (RB)</option>
                        <option value="LEFT_SHOULDER_BOTTOM">LEFT_SHOULDER_BOTTOM (LT)</option>
                        <option value="RIGHT_SHOULDER_BOTTOM">RIGHT_SHOULDER_BOTTOM (RT)</option>
                        <option value="SELECT">SELECT (Back/Share)</option>
                        <option value="START">START (Start/Options)</option>
                        <option value="LEFT_ANALOG_BUTTON">LEFT_ANALOG_BUTTON (L3)</option>
                        <option value="RIGHT_ANALOG_BUTTON">RIGHT_ANALOG_BUTTON (R3)</option>
                        <option value="DPAD_UP">DPAD_UP</option>
                        <option value="DPAD_DOWN">DPAD_DOWN</option>
                        <option value="DPAD_LEFT">DPAD_LEFT</option>
                        <option value="DPAD_RIGHT">DPAD_RIGHT</option>
                        <option value="HOME">HOME (Guide/PS)</option>
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
                
                <div className="field small">
                  <p className="helper text-secondary">
                    {servo.attached_control 
                      ? <><i className="fa-solid fa-check-circle text-success"></i> Currently attached to: <span className="amber-text">{servo.attached_control}</span></>
                      : <><i className="fa-solid fa-info-circle"></i> No gamepad control attached</>
                    }
                  </p>
                </div>
                
                {servo.attached_control && (
                  <div className="field">
                    <button 
                      className="border round"
                      onClick={() => {
                        node.emit('detach_servo', [parseInt(id)]);
                        showToast('Servo detached from gamepad control');
                      }}
                    >
                      <i className="fa-solid fa-unlink left"></i>
                      Detach Control
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Info Tab */}
          {activeTab === 'info' && (
            <div className="tab-panel">
              <div className="card">
                <header>
                  <h5 className="amber-text">Servo Information</h5>
                </header>
                
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
                
                {servo.properties && Object.keys(servo.properties).length > 0 && (
                  <>
                    <div className="divider"></div>
                    <h6 className="amber-text">Advanced Properties</h6>
                    <ul className="list small">
                      {Object.entries(servo.properties).map(([key, value]) => (
                        <li key={key} className="border-bottom">
                          <div className="grid">
                            <div className="s6 text-secondary">{key}</div>
                            <div className="s6 text-right">{value}</div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </article>
      
      <style jsx>{`
        .toast {
          position: fixed;
          right: 1rem;
          top: 1rem;
          max-width: 300px;
          padding: 0.75rem 1rem;
          border-radius: 4px;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
          z-index: 9999;
          animation: fadeInRight 0.3s, fadeOut 0.3s 2.7s;
        }
        
        .toast.success {
          background-color: #4caf50;
          color: white;
        }
        
        .toast.error {
          background-color: #f44336;
          color: white;
        }
        
        .toast.info {
          background-color: #2196f3;
          color: white;
        }
        
        .tabs {
          display: flex;
          overflow-x: auto;
          margin-bottom: 1rem;
          background-color: rgba(0, 0, 0, 0.15);
          border-radius: 8px;
        }
        
        .tab-button {
          flex: 1;
          padding: 0.75rem 0.5rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
          background: transparent;
          color: var(--text);
          border: none;
          border-bottom: 2px solid transparent;
          cursor: pointer;
          min-width: 80px;
        }
        
        .tab-button.active {
          border-bottom: 2px solid var(--primary);
          background-color: rgba(255, 215, 0, 0.1);
        }
        
        .tab-button i {
          font-size: 1.2rem;
        }
        
        .tab-content {
          margin-bottom: 2rem;
        }
        
        .tab-panel {
          animation: fadeIn 0.3s;
        }
        
        .card {
          margin-bottom: 1rem;
          background-color: var(--surface);
          border: 1px solid rgba(255, 215, 0, 0.15);
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          overflow: hidden;
        }
        
        .card header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.75rem 1rem;
          background-color: rgba(255, 215, 0, 0.1);
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .card header h5 {
          margin: 0;
        }
        
        .circular-slider-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 1rem;
          position: relative;
        }
        
        .position-display {
          margin-top: 0.5rem;
        }
        
        .position-display .large {
          font-size: 2rem;
          font-weight: 600;
          color: var(--primary);
        }
        
        .position-display .small {
          font-size: 0.9rem;
          opacity: 0.7;
        }
        
        .actions {
          display: flex;
          gap: 0.5rem;
          padding: 0 1rem 1rem;
        }
        
        .actions button {
          flex: 1;
          padding: 0.75rem;
        }
        
        .field {
          padding: 0.75rem 1rem;
        }
        
        .advanced-settings {
          margin-top: 1rem;
          padding-top: 1rem;
          border-top: 1px dashed rgba(255, 255, 255, 0.1);
        }
        
        .danger-zone {
          margin: 1rem;
          padding: 1rem;
          border: 1px dashed rgba(244, 67, 54, 0.3);
          border-radius: 8px;
          background-color: rgba(244, 67, 54, 0.05);
        }
        
        .mb-2 {
          margin-bottom: 0.5rem;
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes fadeInRight {
          from {
            opacity: 0;
            transform: translateX(20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        @keyframes fadeOut {
          from { opacity: 1; }
          to { opacity: 0; }
        }
        
        @media (max-width: 768px) {
          .tab-button {
            padding: 0.5rem 0.3rem;
            min-width: 70px;
          }
          
          .tab-button i {
            font-size: 1rem;
          }
          
          .tab-button span {
            font-size: 0.8rem;
          }
          
          .circular-slider-container {
            padding: 0.5rem;
          }
          
          .position-display .large {
            font-size: 1.5rem;
          }
          
          .actions {
            flex-direction: column;
          }
          
          .field {
            padding: 0.5rem 0.75rem;
          }
        }
      `}</style>
    </div>
  );
};

export default ServoDebugView;