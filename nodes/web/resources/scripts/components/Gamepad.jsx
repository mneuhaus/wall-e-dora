import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';

const Gamepad = () => {
  const [gamepads, setGamepads] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  
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
    
    // Handle clicks outside dropdown to close it
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    
    return () => {
      window.removeEventListener('gamepadconnected', checkGamepads);
      window.removeEventListener('gamepaddisconnected', checkGamepads);
      document.removeEventListener('mousedown', handleClickOutside);
      clearInterval(interval);
    };
  }, []);
  
  // Format the gamepad name with minimal processing
  const formatGamepadName = (id) => {
    // Just do basic cleanup but preserve the full name
    let name = id
      .replace('Vendor: ', '')
      .replace('Product: ', '')
      .split('(')[0]
      .replace(/\s+/g, ' ')
      .trim();
    
    // If we got an empty name after cleanup, use a generic name
    if (!name) {
      name = 'Game Controller';
    }
    
    return name;
  };
  
  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };
  
  return (
    <div className="dropdown" ref={dropdownRef}>
      <button 
        className="transparent circle" 
        onClick={toggleDropdown}
        aria-label="Gamepads"
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <i className="fa-solid fa-gamepad"></i>
        {gamepads.length > 0 && (
          <span className="badge amber">{gamepads.length}</span>
        )}
      </button>
      
      {isOpen && (
        <div className="menu">
          {gamepads.length > 0 ? (
            gamepads.map(gamepad => (
              <Link 
                key={gamepad.index} 
                to={`/gamepad/${gamepad.index}`}
                className="item"
                onClick={() => setIsOpen(false)}
              >
                <i className="fa-solid fa-gamepad"></i>
                <span className="text">
                  <div>{formatGamepadName(gamepad.id)}</div>
                  <small>Controller #{gamepad.index}</small>
                </span>
              </Link>
            ))
          ) : (
            <div className="item disabled">
              <i className="fa-solid fa-circle-exclamation"></i>
              <span>No gamepads connected</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Gamepad;