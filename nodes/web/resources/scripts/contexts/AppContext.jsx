import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import node from '../Node';
import { normalizeServoList } from '../utils/servoData';

const CAMERA_BACKGROUND_STORAGE_KEY = 'walle.camera-background-enabled';

function getStoredCameraBackgroundEnabled() {
  if (typeof window === 'undefined') {
    return false;
  }

  try {
    return window.localStorage.getItem(CAMERA_BACKGROUND_STORAGE_KEY) === '1';
  } catch (error) {
    return false;
  }
}

// Create the context
const AppContext = createContext(null);

// Create a provider component
export function AppProvider({ children }) {
  const [availableServos, setAvailableServos] = useState([]);
  const [widgetsState, setWidgetsState] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [gamepadProfiles, setGamepadProfiles] = useState({});
  const [cameraBackgroundEnabled, setCameraBackgroundEnabled] = useState(() => getStoredCameraBackgroundEnabled());
  const [photos, setPhotos] = useState([]);
  const [photosLoading, setPhotosLoading] = useState(false);
  const [photoCaptureFlashToken, setPhotoCaptureFlashToken] = useState(0);
  const captureInFlightRef = useRef(false);
  const lastCaptureAtRef = useRef(0);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        CAMERA_BACKGROUND_STORAGE_KEY,
        cameraBackgroundEnabled ? '1' : '0',
      );
    } catch (error) {
      // Ignore storage issues on restricted browsers.
    }
  }, [cameraBackgroundEnabled]);
  
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

      console.log('Received servo_status update:', servoData);

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

  const toggleCameraBackground = () => {
    setCameraBackgroundEnabled((enabled) => !enabled);
  };

  const refreshPhotos = async () => {
    setPhotosLoading(true);
    try {
      const response = await fetch('/api/photos');
      if (!response.ok) {
        throw new Error(`Failed to load photos: ${response.status}`);
      }
      const payload = await response.json();
      setPhotos(Array.isArray(payload.photos) ? payload.photos : []);
    } catch (error) {
      console.error('Failed to load photo gallery', error);
    } finally {
      setPhotosLoading(false);
    }
  };

  const capturePhoto = async (source = 'ui') => {
    if (captureInFlightRef.current) {
      return null;
    }

    captureInFlightRef.current = true;
    try {
      const response = await fetch('/api/photos/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ source }),
      });
      if (!response.ok) {
        throw new Error(`Failed to capture photo: ${response.status}`);
      }

      const payload = await response.json();
      if (payload?.photo) {
        setPhotos((prev) => [payload.photo, ...prev.filter((photo) => photo.filename !== payload.photo.filename)]);
        setPhotoCaptureFlashToken((token) => token + 1);
        window.dispatchEvent(new CustomEvent('photo_saved', { detail: payload.photo }));
        return payload.photo;
      }
      return null;
    } catch (error) {
      console.error('Failed to capture photo', error);
      return null;
    } finally {
      captureInFlightRef.current = false;
    }
  };

  useEffect(() => {
    refreshPhotos();
  }, []);

  useEffect(() => {
    const handleGamepadFlash = (event) => {
      const control = event?.detail?.control;
      if (control !== 'FACE_1') {
        return;
      }

      const now = Date.now();
      if (now - lastCaptureAtRef.current < 1200) {
        return;
      }

      lastCaptureAtRef.current = now;
      capturePhoto('gamepad');
    };

    window.addEventListener('gamepad_button_flash', handleGamepadFlash);
    return () => {
      window.removeEventListener('gamepad_button_flash', handleGamepadFlash);
    };
  }, []);

  // Save a gamepad profile
  const saveGamepadProfile = (profile) => {
    node.emit('save_gamepad_profile', [profile]);
    
    // Update local state
    setGamepadProfiles((prev) => {
      const updated = { ...prev };
      updated[profile.id] = profile;
      return updated;
    });
  };

  // Delete a gamepad profile
  const deleteGamepadProfile = (gamepadId) => {
    node.emit('delete_gamepad_profile', [{ gamepad_id: gamepadId }]);
    
    // Update local state
    setGamepadProfiles((prev) => {
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
    cameraBackgroundEnabled,
    photos,
    photosLoading,
    photoCaptureFlashToken,
    setCameraBackgroundEnabled,
    toggleCameraBackground,
    refreshPhotos,
    capturePhoto,
    setServos: setAvailableServos,
    getServos: () => availableServos,
    updateWidgetsState,
    getWidgetsState: () => widgetsState,
    saveGamepadProfile,
    deleteGamepadProfile,
    node, // Provide the node instance directly
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
