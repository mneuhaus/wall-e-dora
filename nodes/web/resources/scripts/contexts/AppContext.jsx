import React, { createContext, useState, useContext, useEffect } from 'react';
import node from '../Node';

// Create the context
const AppContext = createContext(null);

// Create a provider component
export function AppProvider({ children }) {
  const [availableServos, setAvailableServos] = useState([]);
  const [widgetsState, setWidgetsState] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  
  // Listen for connection status
  useEffect(() => {
    const unsubscribe = node.on('connection', (connected) => {
      setIsConnected(connected);
    });
    
    return unsubscribe;
  }, []);
  
  // Listen for servo status
  useEffect(() => {
    const unsubscribe = node.on('servo_status', (event) => {
      if (event && event.value) {
        setAvailableServos(event.value);
        // Legacy support
        window.availableServos = event.value;
      }
    });
    
    // Request servo status on mount
    node.emit('SCAN', []);
    
    return unsubscribe;
  }, []);
  
  // Update widgets state
  const updateWidgetsState = (state) => {
    setWidgetsState(state);
  };
  
  // Context value
  const value = {
    availableServos,
    widgetsState,
    isConnected,
    setServos: setAvailableServos,
    getServos: () => availableServos,
    updateWidgetsState,
    getWidgetsState: () => widgetsState,
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