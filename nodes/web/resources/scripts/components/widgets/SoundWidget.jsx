import React, { useState, useEffect } from 'react';
import node from '../../Node';

/**
 * SoundWidget - A grid widget for playing sounds
 * 
 * @component
 * @param {Object} props - Component props
 */
const SoundWidget = (props) => {
  const [sounds, setSounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentlyPlaying, setCurrentlyPlaying] = useState(null);
  
  // Request sounds list on mount
  useEffect(() => {
    // Send the correct event to scan for available sounds
    node.emit('scan_sounds', []);
    
    // Listen for sounds list
    const unsubscribe = node.on('available_sounds', (event) => {
      setSounds(event.value || []);
      setLoading(false);
    });
    
    // Set a timeout in case the server doesn't respond
    const timeout = setTimeout(() => {
      setLoading(false);
    }, 3000);
    
    return () => {
      unsubscribe();
      clearTimeout(timeout);
    };
  }, []);
  
  const playSound = (sound) => {
    node.emit('play_sound', [sound]);
    
    // Visual feedback when playing a sound
    setCurrentlyPlaying(sound);
    setTimeout(() => {
      setCurrentlyPlaying(null);
    }, 1000);
  };
  
  const formatSoundName = (sound) => {
    // Remove file extension and convert underscores to spaces
    return sound
      .replace(/\.(mp3|wav|ogg)$/i, '')
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };
  
  // Render loading state
  if (loading) {
    return (
      <div className="loading-state">
        <i className="fas fa-spinner fa-spin"></i>
        <span>Loading sounds...</span>
      </div>
    );
  }
  
  return (
    <div id="sounds" className="small-spacing">
      {sounds.length > 0 ? (
        sounds.map(sound => (
          <div 
            key={sound}
            onClick={() => playSound(sound)}
            className={`sound-item ${currentlyPlaying === sound ? 'playing' : ''}`}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                playSound(sound);
              }
            }}
          >
            <i className={`fas ${currentlyPlaying === sound ? 'fa-volume-high' : 'fa-volume-up'}`}></i>
            <span className="sound-name">{formatSoundName(sound)}</span>
          </div>
        ))
      ) : (
        <div className="empty-state">No sounds available</div>
      )}
    </div>
  );
};

export default SoundWidget;