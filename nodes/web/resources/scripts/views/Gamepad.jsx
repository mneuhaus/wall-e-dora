import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import node from '../Node';

const GamepadView = () => {
  const { index } = useParams();
  const [gamepad, setGamepad] = useState(null);
  const [buttonStates, setButtonStates] = useState([]);
  const [axisStates, setAxisStates] = useState([]);
  
  useEffect(() => {
    // Gamepad polling function
    const pollGamepad = () => {
      const gamepads = navigator.getGamepads();
      const currentGamepad = gamepads[index];
      
      if (currentGamepad) {
        setGamepad(currentGamepad);
        setButtonStates(Array.from(currentGamepad.buttons).map(btn => btn.pressed));
        setAxisStates(Array.from(currentGamepad.axes));
        
        // Send gamepad state to backend
        node.emit('gamepad_state', {
          index: parseInt(index),
          buttons: Array.from(currentGamepad.buttons).map(btn => btn.pressed),
          axes: Array.from(currentGamepad.axes)
        });
      }
    };
    
    // Start polling
    const intervalId = setInterval(pollGamepad, 50);
    
    return () => {
      clearInterval(intervalId);
    };
  }, [index]);
  
  if (!gamepad) {
    return (
      <div className="gamepad-view">
        <h3>Gamepad {index} Not Connected</h3>
        <p>Please connect a gamepad and make sure it's recognized by the browser.</p>
      </div>
    );
  }
  
  return (
    <div className="gamepad-view">
      <h3>Gamepad {index}: {gamepad.id}</h3>
      
      <div className="gamepad-info">
        <h4>Buttons</h4>
        <div className="button-grid">
          {buttonStates.map((pressed, i) => (
            <div key={i} className={`button-indicator ${pressed ? 'active' : ''}`}>
              {i}
            </div>
          ))}
        </div>
        
        <h4>Axes</h4>
        <div className="axis-grid">
          {axisStates.map((value, i) => (
            <div key={i} className="axis-indicator">
              <span>Axis {i}</span>
              <div className="axis-bar-container">
                <div 
                  className="axis-bar" 
                  style={{ width: `${(value + 1) * 50}%` }}
                ></div>
              </div>
              <span>{value.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default GamepadView;