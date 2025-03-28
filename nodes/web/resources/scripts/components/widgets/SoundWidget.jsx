import React, { useState, useEffect } from 'react';
import node from '../../Node';

/**
 * SoundWidget - A widget for playing sounds
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
    // Remove file extension and convert dashes/underscores to spaces
    return sound
      .replace(/\.(mp3|wav|ogg)$/i, '')
      .replace(/[_-]/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };
  
  // Custom styles for the sounds list
  const styles = `
    .sounds-container {
      width: 100%;
      height: 100%;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-right: 5px;
    }
    
    .sound-item {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      background-color: rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    
    .sound-item:hover {
      background-color: rgba(255, 191, 0, 0.15);
    }
    
    .sound-item.playing {
      background-color: rgba(255, 191, 0, 0.3);
    }
    
    .sound-item i {
      margin-right: 10px;
      color: #ffc107;
      font-size: 14px;
      min-width: 14px;
    }
    
    .sound-name {
      font-size: 14px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    
    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      gap: 10px;
      color: rgba(255, 255, 255, 0.7);
    }
    
    .loading-state i {
      font-size: 2rem;
      color: rgba(255, 191, 0, 0.7);
    }
    
    .empty-state {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: rgba(255, 255, 255, 0.7);
    }
  `;
  
  // Render loading state
  if (loading) {
    return (
      <div className="loading-state">
        <style>{styles}</style>
        <i className="fas fa-spinner fa-spin"></i>
        <span>Loading sounds...</span>
      </div>
    );
  }
  
  return (
    <div className="sounds-container">
      <style>{styles}</style>
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