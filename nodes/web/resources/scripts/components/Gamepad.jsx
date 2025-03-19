import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const Gamepad = () => {
  const [gamepads, setGamepads] = useState([]);
  
  useEffect(() => {
    const checkGamepads = () => {
      const connectedGamepads = navigator.getGamepads();
      const gamepadArray = [];
      
      for (let i = 0; i < connectedGamepads.length; i++) {
        if (connectedGamepads[i]) {
          gamepadArray.push({
            index: i,
            id: connectedGamepads[i].id
          });
        }
      }
      
      setGamepads(gamepadArray);
    };
    
    // Check initially
    checkGamepads();
    
    // Add event listeners for gamepad connection/disconnection
    window.addEventListener('gamepadconnected', checkGamepads);
    window.addEventListener('gamepaddisconnected', checkGamepads);
    
    // Poll for gamepad updates
    const interval = setInterval(checkGamepads, 1000);
    
    return () => {
      window.removeEventListener('gamepadconnected', checkGamepads);
      window.removeEventListener('gamepaddisconnected', checkGamepads);
      clearInterval(interval);
    };
  }, []);
  
  return (
    <div className="gamepad-dropdown">
      <button className="transparent circle">
        <i className="fa-solid fa-gamepad"></i>
        {gamepads.length > 0 && (
          <span className="badge">{gamepads.length}</span>
        )}
      </button>
      
      {gamepads.length > 0 && (
        <div className="dropdown-menu">
          {gamepads.map(gamepad => (
            <Link 
              key={gamepad.index} 
              to={`/gamepad/${gamepad.index}`}
              className="dropdown-item"
            >
              Gamepad {gamepad.index}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default Gamepad;