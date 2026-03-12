import React, { createContext, useState, useContext, useEffect } from 'react';
import node from '../Node';
import { normalizeServoList } from '../utils/servoData';

// Create the context
const AppContext = createContext(null);

// Create a provider component
export function AppProvider({ children }) {
  const [availableServos, setAvailableServos] = useState([]);
  const [widgetsState, setWidgetsState] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [gamepadProfiles, setGamepadProfiles] = useState({});
  
  // Listen for connection status
  useEffect(() => {
    const unsubscribe = node.on('connection', (connected) => {
      setIsConnected(connected);
    });
    
    return unsubscribe;
  }, []);
  
  // Listen for servo status updates
  useEffect(() => {
    const unsubscribeStatus = node.on('servo_status', (event) => {
      const servoData = normalizeServoList(event?.value);
      if (servoData.length === 0) {
        return;
      }

      console.log("Received servo_status update:", servoData);

      setAvailableServos((prevServos) => {
        const updatedServos = [...prevServos];

        servoData.forEach((incomingServo) => {
          const existingIndex = updatedServos.findIndex((servo) => servo.id === incomingServo.id);

          if (existingIndex >= 0) {
            updatedServos[existingIndex] = incomingServo;
          } else {
            updatedServos.push(incomingServo);
          }
        });

        window.availableServos = updatedServos;
        return updatedServos;
      });
    });
    
    // Listen for servos_list updates (complete list of available servos)
    const unsubscribeList = node.on('servos_list', (event) => {
      const servosList = normalizeServoList(event?.value);
      if (servosList.length > 0 || Array.isArray(event?.value)) {
        setAvailableServos(servosList);
        window.availableServos = servosList;
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return () => {
      unsubscribeStatus();
      unsubscribeList();
    };
  }, []);

  // Listen for gamepad profiles updates
  useEffect(() => {
    const unsubscribe = node.on('gamepad_profiles_list', (event) => {
      if (event && event.value) {
        const profiles = event.value;
        setGamepadProfiles(profiles);
      }
    });
    
    // Request available gamepad profiles
    node.emit('list_gamepad_profiles', []);
    
    return () => {
      unsubscribe();
    };
  }, []);
  
  // Update widgets state
  const updateWidgetsState = (state) => {
    setWidgetsState(state);
  };

  // Save a gamepad profile
  const saveGamepadProfile = (profile) => {
    node.emit('save_gamepad_profile', [profile]);
    
    // Update local state
    setGamepadProfiles(prev => {
      const updated = { ...prev };
      updated[profile.id] = profile;
      return updated;
    });
  };

  // Delete a gamepad profile
  const deleteGamepadProfile = (gamepadId) => {
    node.emit('delete_gamepad_profile', [{ gamepad_id: gamepadId }]);
    
    // Update local state
    setGamepadProfiles(prev => {
      const updated = { ...prev };
      delete updated[gamepadId];
      return updated;
    });
  };
  
  // Context value
  const value = {
    availableServos,
    widgetsState,
    isConnected,
    gamepadProfiles,
    setServos: setAvailableServos,
    getServos: () => availableServos,
    updateWidgetsState,
    getWidgetsState: () => widgetsState,
    saveGamepadProfile,
    deleteGamepadProfile,
    node // Provide the node instance directly
  };
  
  // Store for debugging
  window.appState = value;
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

// Custom hook for using the app context
export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}
