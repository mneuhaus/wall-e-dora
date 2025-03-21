/**
 * ServoStatus Component
 * 
 * Displays a dropdown menu with the current status of all connected servos.
 * Shows servo ID and current position, with links to the servo debug view.
 * Can be clicked to refresh the servo status.
 * 
 * @component
 */
import React, { useState, useRef, useEffect } from 'react';
import { useAppContext } from '../../contexts/AppContext';
import { Link } from 'react-router-dom';
import node from '../../Node';

const ServoStatus = () => {
  const { availableServos } = useAppContext();
  const [servos, setServos] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  
  // Direct connection to node events for more reliable updates
  useEffect(() => {
    const unsubscribe = node.on('servo_status', (event) => {
      if (event && event.value) {
        setServos(event.value);
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, []);
  
  // Use either direct event data or context data
  const servoData = servos.length > 0 ? servos : (availableServos || []);
  
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
  
  const toggleDropdown = () => {
    setIsOpen(!isOpen);
    // Request fresh data when opening menu
    if (!isOpen) {
      node.emit('SCAN', []);
    }
  };
  
  return (
    <div className="dropdown" ref={dropdownRef}>
      <button 
        className="transparent circle" 
        onClick={toggleDropdown}
        aria-label="Servos"
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <i className={`fa-solid fa-gears ${servoData.length > 0 ? 'amber-text' : ''}`}></i>
        {servoData.length > 0 && (
          <span className="badge amber">{servoData.length}</span>
        )}
      </button>
      
      {isOpen && (
        <div className="menu">
          {servoData.length > 0 ? (
            servoData.map(servo => (
              <Link 
                key={servo.id} 
                to={`/servo/${servo.id}`}
                className="item"
                onClick={() => setIsOpen(false)}
              >
                <i className="fa-solid fa-gear amber-text"></i>
                <span className="text">
                  <div>Servo #{servo.id}</div>
                  <small>Position: {servo.position || 0}</small>
                </span>
              </Link>
            ))
          ) : (
            <div className="item disabled">
              <i className="fa-solid fa-gear"></i>
              <span>No servos connected</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ServoStatus;