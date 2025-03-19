import React, { useState, useEffect } from 'react';
import node from '../Node';

const Power = () => {
  const [voltage, setVoltage] = useState('');
  const [current, setCurrent] = useState('');
  const [power, setPower] = useState('');
  const [runtime, setRuntime] = useState('');
  const [soc, setSoc] = useState('');

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

  // Function to determine which battery icon to show based on SOC
  const getBatteryIcon = () => {
    const socNumber = parseInt(soc) || 0;
    
    if (socNumber <= 0) return 'fa-battery-empty';
    if (socNumber <= 20) return 'fa-battery-quarter';
    if (socNumber <= 50) return 'fa-battery-half';
    if (socNumber <= 80) return 'fa-battery-three-quarters';
    return 'fa-battery-full';
  };

  return (
    <button className="transparent">
      <span>
        <i className={`fa-solid ${getBatteryIcon()}`}></i>
        <span style={{ marginLeft: '10px', display: 'inline-block' }}>{soc} %</span>
      </span>
      <menu className="no-wrap">
        <a>Voltage: {voltage} V</a>
        <a>Current: {current} A</a>
        <a>Power: {power} W</a>
        <a style={{ fontSize: '18px' }}>Runtime: {runtime}</a>
      </menu>
    </button>
  );
};

export default Power;