import React, { useState, useEffect, useRef } from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import node from '../../Node';

/**
 * RandomSoundControl - A control component that plays random sounds at random intervals
 * 
 * @component
 */
const RandomSoundControl = () => {
  const [isActive, setIsActive] = useState(false);
  const [sounds, setSounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const timeoutRef = useRef(null);
  const [pulseEffect, setPulseEffect] = useState(false);
  const isActiveRef = useRef(false); // Reference to track active state consistently
  
  // Request sounds list on mount
  useEffect(() => {
    console.log("RandomSoundControl mounted - scanning for sounds");
    // Send the event to scan for available sounds
    node.emit('scan_sounds', []);
    
    // Listen for sounds list
    const unsubscribe = node.on('available_sounds', (event) => {
      console.log("Received sounds list:", event);
      setSounds(event.value || []);
      setLoading(false);
    });
    
    // Set a timeout in case the server doesn't respond
    const timeout = setTimeout(() => {
      console.log("Audio node timeout - no response received");
      setLoading(false);
    }, 3000);
    
    return () => {
      unsubscribe();
      clearTimeout(timeout);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      isActiveRef.current = false;
    };
  }, []);
  
  // Hook to update the ref when state changes
  useEffect(() => {
    isActiveRef.current = isActive;
    console.log("isActive state changed:", isActive, "isActiveRef is now:", isActiveRef.current);
  }, [isActive]);
  
  // Function to play a random sound
  const playRandomSound = () => {
    console.log("playRandomSound called, isActiveRef.current:", isActiveRef.current);
    
    if (sounds.length === 0 || !isActiveRef.current) {
      console.log("Early return - conditions not met for playing sounds");
      return;
    }
    
    // Pick a random sound
    const randomIndex = Math.floor(Math.random() * sounds.length);
    const randomSound = sounds[randomIndex];
    
    console.log("Playing random sound:", randomSound);
    
    try {
      // Play the sound using SoundWidget's approach
      node.emit('play_sound', [randomSound]);
      
      // Visual feedback
      setPulseEffect(true);
      setTimeout(() => {
        setPulseEffect(false);
      }, 1000);
    } catch (error) {
      console.error("Error playing sound:", error);
    }
    
    // Only schedule the next sound if still active
    if (isActiveRef.current) {
      // Schedule the next sound with a random delay between 5-10 seconds
      const minDelay = 5000;
      const maxDelay = 10000;
      const randomDelay = Math.floor(Math.random() * (maxDelay - minDelay)) + minDelay;
      
      console.log(`Scheduling next sound in ${randomDelay/1000} seconds, isActiveRef.current:`, isActiveRef.current);
      
      timeoutRef.current = setTimeout(() => {
        console.log("Timeout fired, isActiveRef.current:", isActiveRef.current);
        if (isActiveRef.current) {
          playRandomSound();
        } else {
          console.log("Timeout fired but component is no longer active");
        }
      }, randomDelay);
    }
  };
  
  // Play first random sound
  const startRandomSounds = () => {
    if (sounds.length === 0) return;
    
    console.log("Starting random sounds, setting isActiveRef.current = true");
    isActiveRef.current = true;
    
    // Play a sound immediately
    const randomIndex = Math.floor(Math.random() * sounds.length);
    const randomSound = sounds[randomIndex];
    console.log("Playing first random sound:", randomSound);
    
    try {
      node.emit('play_sound', [randomSound]);
      
      // Visual feedback
      setPulseEffect(true);
      setTimeout(() => {
        setPulseEffect(false);
      }, 1000);
      
      // Schedule the next sound
      const minDelay = 5000;
      const maxDelay = 10000;
      const randomDelay = Math.floor(Math.random() * (maxDelay - minDelay)) + minDelay;
      
      console.log(`Scheduling next sound in ${randomDelay/1000} seconds`);
      
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        console.log("First timeout fired, isActiveRef.current:", isActiveRef.current);
        if (isActiveRef.current) {
          playRandomSound();
        }
      }, randomDelay);
    } catch (error) {
      console.error("Error playing first sound:", error);
    }
  };
  
  // Stop random sounds
  const stopRandomSounds = () => {
    console.log("Stopping random sounds, setting isActiveRef.current = false");
    isActiveRef.current = false;
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };
  
  // Toggle active state
  const toggleActive = () => {
    const newActive = !isActive;
    console.log("Toggle called, current:", isActive, "new:", newActive);
    setIsActive(newActive);
    
    if (newActive) {
      console.log("Starting random sound playback... Available sounds:", sounds.length);
      startRandomSounds();
    } else {
      console.log("Stopping random sound playback");
      stopRandomSounds();
    }
  };
  
  // Button is disabled if no sounds are available
  const isDisabled = loading || sounds.length === 0;

  return (
    <Tooltip label={isActive ? "Turn off random sounds" : "Turn on random sounds"} withArrow position="bottom">
      <div style={{ position: 'relative' }}>
        <ActionIcon
          variant="subtle"
          color={isActive ? "amber" : "gray"}
          onClick={toggleActive}
          disabled={isDisabled}
          aria-label="Toggle random sounds"
          className={pulseEffect ? 'pulse' : ''}
        >
          <i className={`fas fa-shuffle ${isActive ? 'amber-text' : ''}`}></i>
        </ActionIcon>
        {isActive && (
          <span 
            style={{
              position: 'absolute',
              top: -5,
              right: -5,
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: '#ffc107',
              animation: 'pulse 1s infinite alternate'
            }}
          />
        )}
      </div>
    </Tooltip>
  );
};

export default RandomSoundControl;