/**
 * ServoSelector Component
 * 
 * A dropdown selector component for choosing servos.
 * Displays available servos with their IDs and names.
 * Handles selection and provides the servo ID to the parent component.
 * 
 * @component
 */
import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../../../contexts/AppContext';
import node from '../../../Node';

// Use portal for dropdown to escape the re-rendering parent components
const createPortal = (content) => {
  if (typeof document === 'undefined') return null;
  
  // Create or get the portal element
  let portalElement = document.getElementById('dropdown-portal');
  if (!portalElement) {
    portalElement = document.createElement('div');
    portalElement.id = 'dropdown-portal';
    portalElement.style.position = 'fixed';
    portalElement.style.top = '0';
    portalElement.style.left = '0';
    portalElement.style.width = '100%';
    portalElement.style.height = '100%';
    portalElement.style.zIndex = '9999';
    portalElement.style.pointerEvents = 'none';
    document.body.appendChild(portalElement);
  }
  
  // Create a container for this dropdown
  const container = document.createElement('div');
  container.style.pointerEvents = 'auto';
  portalElement.appendChild(container);
  
  // Render the content into the portal
  const renderPortal = () => {
    // Use a basic DOM-based approach for rendering
    container.innerHTML = '';
    if (typeof content === 'string') {
      container.innerHTML = content;
    } else if (content instanceof HTMLElement) {
      container.appendChild(content);
    }
  };
  
  renderPortal();
  
  return {
    update: renderPortal,
    remove: () => {
      if (container.parentNode) {
        container.parentNode.removeChild(container);
      }
    }
  };
};

const ServoSelector = ({ value, onChange, label }) => {
  const { availableServos } = useAppContext();
  const [isOpen, setIsOpen] = useState(false);
  const [selectedServo, setSelectedServo] = useState(null);
  const [cachedServos, setCachedServos] = useState([]);
  const dropdownRef = useRef(null);
  const buttonRef = useRef(null);
  const portalRef = useRef(null);
  const originalListeners = useRef(null);
  
  // Initialize cached servos once
  useEffect(() => {
    if (availableServos && availableServos.length > 0 && !isOpen) {
      setCachedServos([...availableServos]);
      
      // Update selected servo info
      if (value) {
        const selectedId = parseInt(value);
        const servo = availableServos.find(s => {
          const currentId = typeof s.id === 'string' ? parseInt(s.id) : s.id;
          return currentId === selectedId;
        });
        
        if (servo) {
          setSelectedServo(servo);
        }
      }
    }
  }, [value, availableServos, isOpen]);

  // When dropdown opens, disable Node event handlers
  useEffect(() => {
    if (isOpen) {
      // Temporarily disable servo status updates
      if (node && node.emitter) {
        // Save original listeners
        originalListeners.current = { ...node.emitter.all };
        
        // Remove servo_status event listeners
        node.emitter.off('servo_status');
      }
      
      // Create the dropdown element
      const createDropdownElement = () => {
        const rect = buttonRef.current?.getBoundingClientRect();
        if (!rect) return null;
        
        const dropdown = document.createElement('div');
        dropdown.className = 'servo-selector-dropdown';
        dropdown.style.position = 'absolute';
        dropdown.style.top = `${rect.bottom + window.scrollY}px`;
        dropdown.style.left = `${rect.left + window.scrollX}px`;
        dropdown.style.width = `${rect.width}px`;
        dropdown.style.zIndex = '10000';
        dropdown.style.maxHeight = '300px';
        dropdown.style.overflowY = 'auto';
        dropdown.style.backgroundColor = 'var(--surface)';
        dropdown.style.border = '1px solid rgba(255, 215, 0, 0.3)';
        dropdown.style.borderRadius = '6px';
        dropdown.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.3)';
        
        // Add "None" option
        const noneOption = document.createElement('div');
        noneOption.className = 'servo-selector-option';
        noneOption.style.padding = '10px 16px';
        noneOption.style.cursor = 'pointer';
        noneOption.style.borderBottom = '1px solid rgba(255, 255, 255, 0.05)';
        noneOption.innerHTML = '<div class="servo-option-text">None</div>';
        noneOption.addEventListener('click', () => handleSelectServo(null));
        dropdown.appendChild(noneOption);
        
        // Add servo options
        cachedServos.forEach(servo => {
          const option = document.createElement('div');
          option.className = `servo-selector-option ${parseInt(value) === parseInt(servo.id) ? 'selected' : ''}`;
          option.style.padding = '10px 16px';
          option.style.cursor = 'pointer';
          option.style.borderBottom = '1px solid rgba(255, 255, 255, 0.05)';
          if (parseInt(value) === parseInt(servo.id)) {
            option.style.backgroundColor = 'rgba(255, 215, 0, 0.2)';
          }
          option.innerHTML = `
            <div class="servo-option-text">
              ${servo.alias ? `${servo.alias} <span style="font-size: 12px; opacity: 0.7;">(#${servo.id})</span>` : `Servo #${servo.id}`}
            </div>
          `;
          option.addEventListener('click', () => handleSelectServo(servo.id));
          dropdown.appendChild(option);
        });
        
        return dropdown;
      };
      
      // Create and position the dropdown
      const dropdownElement = createDropdownElement();
      if (dropdownElement) {
        portalRef.current = createPortal(dropdownElement);
        
        // Add global click handler for closing
        const handleGlobalClick = (e) => {
          if (!dropdownElement.contains(e.target) && e.target !== buttonRef.current) {
            closeDropdown();
          }
        };
        
        setTimeout(() => {
          document.addEventListener('click', handleGlobalClick);
        }, 100);
        
        // Save the click handler for cleanup
        dropdownElement._clickHandler = handleGlobalClick;
      }
    }

    return () => {
      if (!isOpen && originalListeners.current) {
        // Restore original listeners
        Object.entries(originalListeners.current).forEach(([event, handlers]) => {
          handlers.forEach(handler => {
            node.emitter.on(event, handler);
          });
        });
        originalListeners.current = null;
      }
      
      // Remove the dropdown if it exists
      if (portalRef.current) {
        portalRef.current.remove();
        portalRef.current = null;
      }
    };
  }, [isOpen, cachedServos, value]);

  const closeDropdown = () => {
    // Remove document click listener
    if (portalRef.current) {
      document.removeEventListener('click', portalRef.current._clickHandler);
      portalRef.current.remove();
      portalRef.current = null;
    }
    
    setIsOpen(false);
  };

  const handleSelectServo = (servoId) => {
    closeDropdown();
    
    // Normalize the servo ID to ensure consistency
    const normalizedId = servoId === null ? null : parseInt(servoId);
    console.log(`ServoSelector selected: ${normalizedId}`);
    
    // Delay to ensure proper timing but use a higher priority task
    setTimeout(() => {
      // Call the change handler with the normalized ID
      onChange(normalizedId);
      
      // For debugging
      console.log(`ServoSelector onChange called with: ${normalizedId}`);
    }, 50);
  };

  const toggleDropdown = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsOpen(!isOpen);
  };

  return (
    <div className="servo-selector" ref={dropdownRef}>
      <label className="servo-selector-label">{label || 'Select Servo'}</label>
      <button 
        className="servo-selector-button" 
        onClick={toggleDropdown}
        ref={buttonRef}
        type="button"
      >
        {selectedServo ? 
          (selectedServo.alias ? `${selectedServo.alias} (#${selectedServo.id})` : `Servo #${selectedServo.id}`) 
          : 'None Selected'}
        <i className={`fas fa-chevron-${isOpen ? 'up' : 'down'}`}></i>
      </button>
    </div>
  );
};

export default ServoSelector;