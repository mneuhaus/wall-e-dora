import React, { createContext, useState, useContext, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppContext } from './AppContext';

// Create the context
const GridContext = createContext(null);

// LocalStorage key for fallback persistence - must match key in GridLock.jsx
export const STORAGE_KEY = 'wall-e-dora-grid-layout';

// Create a provider component
export function GridProvider({ children }) {
  const [layout, setLayout] = useState([]);
  const [isEditable, setIsEditable] = useState(false);
  const [widgetsState, setWidgetsState] = useState({});
  const [backendSynced, setBackendSynced] = useState(false);
  const [backendInitialized, setBackendInitialized] = useState(false);
  const gridLayoutRef = useRef(null);
  const { node } = useAppContext();
  
  // Listen for initial grid state from the HTML template
  useEffect(() => {
    const handleInitialGridState = (e) => {
      const initialGridState = e.detail;
      
      if (initialGridState && Object.keys(initialGridState).length > 0) {
        console.log("Using initial grid state from server template:", initialGridState);
        initializeGrid(initialGridState);
        setBackendSynced(true);
        
        // Save to localStorage as fallback
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(initialGridState));
        } catch (error) {
          console.error("Error saving to localStorage:", error);
        }
      }
    };
    
    // Listen for the custom event from main.js
    document.addEventListener('grid_state_initialized', handleInitialGridState);
    
    return () => {
      document.removeEventListener('grid_state_initialized', handleInitialGridState);
    };
  }, []);
  
  // Listen for backend widget state updates via WebSocket
  useEffect(() => {
    // Only set up this effect if we have an active node connection
    if (!node) return;
    
    const handleWidgetsState = (event) => {
      const receivedWidgetsData = event.value || {};
      
      // Debug received data structure
      console.log("Raw received widget data:", JSON.stringify(receivedWidgetsData, null, 2));
      
      // Only initialize from backend if we have data and haven't synced yet
      // or if this is an update from another client
      if (Object.keys(receivedWidgetsData).length > 0) {
        console.log("Received backend widget state via WebSocket:", receivedWidgetsData);
        initializeGrid(receivedWidgetsData);
        
        // Save to localStorage as fallback
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(receivedWidgetsData));
        } catch (error) {
          console.error("Error saving to localStorage:", error);
        }
        
        setBackendSynced(true);
      } else if (!backendSynced) {
        // If backend has no data and we haven't synced yet, try localStorage as fallback
        try {
          const savedLayout = localStorage.getItem(STORAGE_KEY);
          if (savedLayout) {
            const parsedState = JSON.parse(savedLayout);
            console.log("Using localStorage fallback:", parsedState);
            initializeGrid(parsedState);
            
            // Push the localStorage data to the backend
            saveWidgetsState(parsedState);
          }
        } catch (error) {
          console.error("Error loading layout from localStorage:", error);
        }
      }
      
      setBackendInitialized(true);
    };
    
    // Listen for grid state updates via WebSocket
    const unsubscribe = node.on('grid_state', handleWidgetsState);
    
    // Request the latest grid state from backend
    // This is needed when multiple clients are connected to ensure we have the latest state
    node.emit('get_grid_state', []);
    
    return unsubscribe;
  }, [node, backendSynced]);
  
  // Toggle grid editing mode
  const toggleGridEditing = () => {
    console.log('Before toggle - isEditable was:', isEditable);
    setIsEditable(prevState => !prevState);
    console.log('Grid editing mode toggled');
    
    // Force layout update to refresh the grid with new settings
    if (layout && layout.length > 0) {
      console.log('Forcing layout update with items:', layout.length);
      setTimeout(() => {
        const updatedLayout = [...layout];
        setLayout(updatedLayout);
      }, 0);
    }
  };
  
  // Add a widget to the grid
  const addWidget = (type, config = {}) => {
    const widgetId = `widget-${uuidv4()}`;
    const widgetConfig = {
      ...config,
      type,
      i: widgetId,
      x: 0,
      y: Math.max(0, ...layout.map(item => item.y + item.h), 0),
      w: config.w || 3,
      h: config.h || 4,
      minW: config.minW || 2,
      minH: config.minH || 2,
    };
    
    // Add to layout
    const newLayout = [...layout, widgetConfig];
    setLayout(newLayout);
    
    // Save widget to state
    const newWidgetsState = { ...widgetsState, [widgetId]: widgetConfig };
    setWidgetsState(newWidgetsState);
    
    // Save to backend (primary storage)
    saveWidgetsState(newWidgetsState);
    
    // Save to localStorage (fallback)
    saveToLocalStorage(newWidgetsState);
    
    return widgetId;
  };
  
  // Remove a widget from the grid
  const removeWidget = (widgetId) => {
    const index = layout.findIndex(item => item.i === widgetId);
    if (index !== -1) {
      const newLayout = [...layout];
      newLayout.splice(index, 1);
      setLayout(newLayout);
      
      // Remove from widgets state
      const newWidgetsState = { ...widgetsState };
      delete newWidgetsState[widgetId];
      setWidgetsState(newWidgetsState);
      
      // Save to backend (primary storage)
      saveWidgetsState(newWidgetsState);
      
      // Save to localStorage (fallback)
      saveToLocalStorage(newWidgetsState);
    }
  };
  
  // Convert legacy widget state to React Grid Layout format
  const convertLegacyWidgetsState = (oldState) => {
    const newLayout = [];
    
    if (!oldState) return newLayout;
    
    Object.entries(oldState).forEach(([widgetId, config]) => {
      // Create a layout item from the old config
      // Make sure the type property is preserved and has higher precedence
      const widgetType = config.type || 'unknown';
      
      console.log(`Converting widget ${widgetId} with type: ${widgetType}`);
      
      newLayout.push({
        i: widgetId,
        x: config.x || 0,
        y: config.y || 0,
        w: config.w || 3,
        h: config.h || 4,
        type: widgetType,
        ...config,
        // Re-specify the type to ensure it's not overwritten by ...config
        type: widgetType
      });
    });
    
    return newLayout;
  };
  
  // Handle layout changes
  const onLayoutChange = (newLayout) => {
    console.log('Layout updated:', newLayout);
    
    // Ensure all widgets have a proper type
    const fixedLayout = newLayout.map(item => {
      if (!item.type || item.type === 'unknown') {
        // Try to get the type from the existing state
        const existingWidget = widgetsState[item.i];
        const widgetType = existingWidget?.type || 'unknown';
        console.warn(`Widget ${item.i} missing type in layout update, using: ${widgetType}`);
        return { ...item, type: widgetType };
      }
      return item;
    });
    
    setLayout(fixedLayout);
    const newWidgetsState = layoutToWidgetsState(fixedLayout);
    setWidgetsState(newWidgetsState);
    
    // Save to backend (primary storage)
    saveWidgetsState(newWidgetsState);
    
    // Save to localStorage (fallback)
    saveToLocalStorage(newWidgetsState);
  };
  
  // Convert layout to widgets state format for saving
  const layoutToWidgetsState = (layoutItems) => {
    const state = {};
    
    layoutItems.forEach(item => {
      state[item.i] = { ...item };
    });
    
    return state;
  };
  
  // Save widgets state to backend
  const saveWidgetsState = (state) => {
    const stateToSave = state || widgetsState;
    
    // Ensure each widget in the state has a valid type
    Object.keys(stateToSave).forEach(widgetId => {
      if (!stateToSave[widgetId].type || stateToSave[widgetId].type === 'unknown') {
        console.warn(`Widget ${widgetId} has invalid type, setting to default for debugging`);
        stateToSave[widgetId].type = stateToSave[widgetId].type || 'sounds-widget';
      }
    });
    
    console.log("Saving grid layout to backend:", JSON.stringify(stateToSave, null, 2));
    node.emit('save_grid_state', stateToSave);
  };
  
  // Save widgets state to localStorage as fallback
  const saveToLocalStorage = (state) => {
    try {
      const stateToSave = state || widgetsState;
      
      // Ensure each widget in the state has a valid type (same as in saveWidgetsState)
      Object.keys(stateToSave).forEach(widgetId => {
        if (!stateToSave[widgetId].type || stateToSave[widgetId].type === 'unknown') {
          console.warn(`Widget ${widgetId} has invalid type in localStorage, fixing`);
          stateToSave[widgetId].type = stateToSave[widgetId].type || 'sounds-widget';
        }
      });
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
      console.log("Saved grid layout to localStorage (fallback)");
    } catch (error) {
      console.error("Error saving to localStorage:", error);
    }
  };
  
  // Reset grid layout
  const resetGridLayout = () => {
    // Empty the grid
    setLayout([]);
    setWidgetsState({});
    
    // Save the empty state to both backend and localStorage
    saveWidgetsState({});
    saveToLocalStorage({});
    
    // We don't need a dedicated reset event since saving an empty state
    // effectively resets the grid on all devices
    console.log("Grid layout reset");
  };
  
  // Initialize grid with saved state
  const initializeGrid = (savedState) => {
    const receivedWidgetsData = savedState || {};
    setWidgetsState(receivedWidgetsData);
    const newLayout = convertLegacyWidgetsState(receivedWidgetsData);
    
    // Extra validation to ensure all widgets have a type
    const validatedLayout = newLayout.map(item => {
      if (!item.type) {
        console.warn(`Widget ${item.i} is missing type property, defaulting to 'unknown'`);
        return { ...item, type: 'unknown' };
      }
      return item;
    });
    
    setLayout(validatedLayout);
    console.log("Initialized grid with saved state:", validatedLayout);
  };
  
  // Context value
  const value = {
    layout,
    isEditable,
    widgetsState,
    backendSynced,
    backendInitialized,
    gridLayoutRef,
    toggleGridEditing,
    addWidget,
    removeWidget,
    onLayoutChange,
    initializeGrid,
    saveWidgetsState,
    saveToLocalStorage,
    resetGridLayout
  };
  
  return (
    <GridContext.Provider value={value}>
      {children}
    </GridContext.Provider>
  );
}

// Custom hook for using the grid context
export function useGridContext() {
  const context = useContext(GridContext);
  if (!context) {
    throw new Error('useGridContext must be used within a GridProvider');
  }
  return context;
}