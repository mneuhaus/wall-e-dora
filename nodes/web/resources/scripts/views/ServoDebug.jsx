import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import node from '../Node';
import Slider from 'rc-slider';

const ServoDebug = () => {
  const { id } = useParams();
  const [servo, setServo] = useState(null);
  const [position, setPosition] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [speed, setSpeed] = useState(100);
  const [min, setMin] = useState(0);
  const [max, setMax] = useState(1024);
  const [newId, setNewId] = useState('');
  const [aliasInput, setAliasInput] = useState('');
  const [attachType, setAttachType] = useState("button");
  const [attachIndex, setAttachIndex] = useState("");
  
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
        
        // Map servo position (min-max) to UI range (0-180)
        const uiPosition = Math.round(
          300 * (servoPosition - servoMinPos) / (servoMaxPos - servoMinPos)
        );
        
        console.log(`Mapped servo ${servoPosition} to UI position ${uiPosition}°`);
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
      console.log("UI position:", positionValue);
      
      // Update the local state immediately for responsive UI
      setPosition(positionValue);
      
      // Map UI slider value (0-300) to servo range (min-max)
      let servoMinPos = min || 0;
      let servoMaxPos = max || 4095;
      
      // Linear mapping from UI range (0-300) to servo range
      const servoPosition = Math.round(
        servoMinPos + (positionValue / 300) * (servoMaxPos - servoMinPos)
      );
      
      console.log(`Mapped ${positionValue}° to servo position ${servoPosition}`);
      
      // Use stronger debounce to limit servo commands
      clearTimeout(window.servoUpdateTimeout);
      window.servoUpdateTimeout = setTimeout(() => {
        // Only send if position hasn't changed in the debounce period
        console.log("Sending to servo:", servoPosition);
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
          
  const handleAttachServo = () => {
    node.emit('attach_servo', [parseInt(id), attachType, attachIndex]);
    alert(`Attached servo ${id} to ${attachType} ${attachIndex}`);
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
        {/* Header Section */}
        <header className="servo-header m-bottom-2">
          <div className="breadcrumb">
            <Link to="/" className="small">Home</Link>
            <span className="small">/</span>
            <span className="small" aria-current="page">Servo {id}</span>
          </div>
          <h1 className="m-top-1">Servo Control Panel</h1>
          <p className="text-gray">Use the controls below to adjust position, speed, and calibration settings for the servo.</p>
        </header>

        <div className="grid gap-2">
          {/* Position Control Section */}
          <div className="s12 m6 l4">
            <section className="card p-3 position-control">
              <h6 className="m-bottom-2">Position Control</h6>
              <div className="control-group" role="group" aria-label="Position control">
                <div className="slider-wrapper">
                  <Slider
                    min={0}
                    max={300}
                    value={position}
                    onChange={handlePositionChange}
                    railStyle={{ backgroundColor: "rgba(55, 71, 79, 0.3)" }}
                    trackStyle={{ backgroundColor: "var(--primary)" }}
                    handleStyle={{ borderColor: "var(--primary)" }}
                  />
                  <div className="slider-value">Position: {position}°</div>
                </div>
                <div className="slider-control m-top-2">
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

          {/* Status & Calibration Section */}
          <div className="s12 m6 l4">
            <section className="card p-3 status-section m-bottom-2">
              <h6 className="m-bottom-2">Servo Status</h6>
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
              <section className="card p-3 calibration-section">
                <h6 className="m-bottom-2">Calibration Range</h6>
                <div className="status-grid">
                  <div className="status-item p-1">
                    <span className="label text-gray">Min Pos</span>
                    <span className="value">{servo.min_pos || 'Not calibrated'}</span>
                  </div>
                  <div className="status-item p-1">
                    <span className="label text-gray">Max Pos</span>
                    <span className="value">{servo.max_pos || 'Not calibrated'}</span>
                  </div>
                </div>
              </section>
            )}
          </div>

          {/* Configuration Section */}
          <div className="s12 m12 l4">
            <section className="card p-3 config-section">
              <h6 className="m-bottom-2">Servo Configuration</h6>
              <div className="config-inputs">
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
              </div>
              <div className="config-attach m-bottom-2" style={{ display: 'flex', alignItems: 'center' }}>
                  <select value={attachType} onChange={(e) => setAttachType(e.target.value)} aria-label="Control Type">
                    <option value="button">Button</option>
                    <option value="axis">Axis</option>
                  </select>
                  { attachType === 'button' ? (
                    <select value={attachIndex} onChange={(e) => setAttachIndex(e.target.value)} aria-label="Control Name" style={{ width: '200px', marginLeft: '10px' }}>
                      <option value="">Select Button</option>
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
                    </select>
                  ) : (
                    <select value={attachIndex} onChange={(e) => setAttachIndex(e.target.value)} aria-label="Control Name" style={{ width: '200px', marginLeft: '10px' }}>
                      <option value="">Select Axis</option>
                      <option value="LEFT_ANALOG_STICK_X">LEFT_ANALOG_STICK_X</option>
                      <option value="LEFT_ANALOG_STICK_Y">LEFT_ANALOG_STICK_Y</option>
                      <option value="RIGHT_ANALOG_STICK_X">RIGHT_ANALOG_STICK_X</option>
                      <option value="RIGHT_ANALOG_STICK_Y">RIGHT_ANALOG_STICK_Y</option>
                    </select>
                  )}
                  <button onClick={handleAttachServo} disabled={attachIndex === ''} aria-label="Attach servo to gamepad control" style={{ marginLeft: '10px' }}>
                    Attach to Gamepad
                  </button>
              </div>
              <div className="config-actions m-top-2">
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
              <div className="divider m-top-3 m-bottom-3"></div>
              <button 
                className="border error p-2 full-width"
                onClick={handleResetServo}
                aria-label="Reset servo to factory defaults"
              >
                <i className="fa-solid fa-rotate-left m-right-1"></i>
                Reset to Factory Defaults
              </button>
            </section>
          </div>
        </div>
      </article>
    </div>
  );
};

export default ServoDebug;
