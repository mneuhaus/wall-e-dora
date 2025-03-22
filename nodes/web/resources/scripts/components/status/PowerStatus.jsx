/**
 * PowerStatus Component
 * 
 * Displays power status information for the robot.
 * Shows battery level, voltage, current, power consumption, and estimated runtime.
 * Includes battery capacity estimation and discharge rate information.
 * 
 * @component
 */
import React, { useState, useEffect, useRef } from 'react';
import node from '../../Node';

const PowerStatus = () => {
  const [voltage, setVoltage] = useState('');
  const [current, setCurrent] = useState('');
  const [power, setPower] = useState('');
  const [runtime, setRuntime] = useState('');
  const [soc, setSoc] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [capacity, setCapacity] = useState(2.5); // Default capacity in Ah
  const [dischargeRate, setDischargeRate] = useState(0); // % per hour
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
      console.log("Raw runtime event:", event);
      
      // Handle array values (most likely case from pyarrow)
      let runtimeValue;
      if (Array.isArray(event.value)) {
        runtimeValue = event.value[0];
      } else {
        runtimeValue = event.value;
      }
      
      // Convert to number and validate
      runtimeValue = parseFloat(runtimeValue);
      
      // If not a valid number, use 0
      if (isNaN(runtimeValue) || !isFinite(runtimeValue) || runtimeValue < 0) {
        runtimeValue = 0;
      }
      
      console.log("Processed runtime:", runtimeValue);
      setRuntime(runtimeValue);
    });
    
    // Subscribe to new capacity and discharge rate events
    const capacityUnsub = node.on('capacity', (event) => {
      setCapacity(parseFloat(event.value).toFixed(2));
    });
    
    const dischargeRateUnsub = node.on('discharge_rate', (event) => {
      setDischargeRate(parseFloat(event.value).toFixed(1));
    });
    
    // Cleanup subscriptions
    return () => {
      voltageUnsub();
      currentUnsub();
      powerUnsub();
      socUnsub();
      runtimeUnsub();
      capacityUnsub();
      dischargeRateUnsub();
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
  
  // Format runtime from seconds to HH:MM format
  const formatRuntime = (seconds) => {
    console.log("Formatting runtime:", seconds, "Type:", typeof seconds);
    
    // Handle all possible invalid cases
    if (seconds === Infinity || seconds === "Infinity" || 
        isNaN(seconds) || seconds <= 0 || seconds === undefined) {
      return "--:--";
    }
    
    // Ensure seconds is a number
    const secondsNum = Number(seconds);
    
    const hours = Math.floor(secondsNum / 3600);
    const minutes = Math.floor((secondsNum % 3600) / 60);
    console.log("Formatted runtime:", hours, ":", minutes);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
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
        <div className="menu">
          <div className="item" style={{ flexDirection: 'column', alignItems: 'start' }}>
            <div className="padded power-info">
              <div><i className="fa-solid fa-bolt amber-text"></i> Voltage: {voltage} V</div>
              <div><i className="fa-solid fa-gauge-high amber-text"></i> Current: {current} A</div>
              <div><i className="fa-solid fa-plug amber-text"></i> Power: {power} W</div>
              <div><i className="fa-solid fa-clock amber-text"></i> Runtime: {formatRuntime(runtime)}</div>
              <div><i className="fa-solid fa-battery-full amber-text"></i> Capacity: {capacity} Ah</div>
              <div><i className="fa-solid fa-arrow-trend-down amber-text"></i> Discharge: {dischargeRate}%/hr</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PowerStatus;