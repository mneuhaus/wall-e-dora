import React, { useState, useEffect, useRef } from 'react';
import node from '../Node';

const Power = () => {
  const [voltage, setVoltage] = useState('');
  const [current, setCurrent] = useState('');
  const [power, setPower] = useState('');
  const [runtime, setRuntime] = useState('');
  const [soc, setSoc] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    // Subscribe to battery/power events
    const voltageUnsub = node.on('voltage', (event) => {
      setVoltage(parseFloat(event.value).toFixed(2));
    });
    
    const currentUnsub = node.on('current', (event) => {
      setCurrent(parseFloat(event.value).toFixed(2));
    });
    
    const powerUnsub = node.on('power', (event) => {
      setPower(parseFloat(event.value).toFixed(2));
    });
    
    const socUnsub = node.on('soc', (event) => {
      setSoc(parseFloat(event.value).toFixed(0));
    });
    
    const runtimeUnsub = node.on('runtime', (event) => {
      setRuntime(event.value);
    });
    
    // Cleanup subscriptions
    return () => {
      voltageUnsub();
      currentUnsub();
      powerUnsub();
      socUnsub();
      runtimeUnsub();
    };
  }, []);
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Function to determine which battery icon to show based on SOC
  const getBatteryIcon = () => {
    const socNumber = parseInt(soc) || 0;
    
    if (socNumber <= 0) return 'fa-battery-empty';
    if (socNumber <= 20) return 'fa-battery-quarter';
    if (socNumber <= 50) return 'fa-battery-half';
    if (socNumber <= 80) return 'fa-battery-three-quarters';
    return 'fa-battery-full';
  };
  
  // Function to determine battery status color
  const getBatteryStatusColor = () => {
    const socNumber = parseInt(soc) || 0;
    
    if (socNumber <= 20) return 'red-text';
    if (socNumber <= 50) return 'amber-text';
    return 'green-text';
  };
  
  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="dropdown" ref={dropdownRef}>
      <button 
        className="transparent"
        aria-label="Battery Status"
        aria-haspopup="true"
        aria-expanded={isOpen}
        onClick={toggleDropdown}
      >
        <span>
          <i className={`fa-solid ${getBatteryIcon()} ${getBatteryStatusColor()}`}></i>
          <span style={{ marginLeft: '3px', display: 'inline-block' }}>{soc}%</span>
        </span>
      </button>
      {isOpen && (
        <div 
          className="menu"
          style={{
            top: dropdownRef.current ? dropdownRef.current.getBoundingClientRect().bottom + 'px' : '50px',
            left: dropdownRef.current ? dropdownRef.current.getBoundingClientRect().left + 'px' : 'auto',
            right: dropdownRef.current ? (window.innerWidth - dropdownRef.current.getBoundingClientRect().right) + 'px' : 'auto'
          }}
        >
          <div className="item" style={{ flexDirection: 'column', alignItems: 'start' }}>
            <div className="padded power-info">
              <div><i className="fa-solid fa-bolt amber-text"></i> Voltage: {voltage} V</div>
              <div><i className="fa-solid fa-gauge-high amber-text"></i> Current: {current} A</div>
              <div><i className="fa-solid fa-plug amber-text"></i> Power: {power} W</div>
              <div><i className="fa-solid fa-clock amber-text"></i> Runtime: {runtime}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Power;