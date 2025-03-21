/**
 * VolumeControl Component
 * 
 * A control for adjusting the audio volume.
 * Provides a dropdown with a slider to adjust the volume level.
 * 
 * @component
 */
import React, { useState, useRef, useEffect } from 'react';
import node from '../../Node';

const VolumeControl = () => {
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);
  const [volume, setVolume] = useState(50);
  const volumeRef = useRef(null);
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (volumeRef.current && !volumeRef.current.contains(event.target)) {
        setShowVolumeSlider(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleVolumeSlider = () => {
    setShowVolumeSlider(!showVolumeSlider);
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseInt(e.target.value);
    setVolume(newVolume);
    node.emit('set_volume', [newVolume]);
  };

  const getVolumeIcon = () => {
    // Using class names that match Font Awesome
    if (volume <= 0) return 'fa-volume-off';
    if (volume <= 30) return 'fa-volume-down';
    if (volume <= 70) return 'fa-volume-down';
    return 'fa-volume-up';
  };

  return (
    <div className="dropdown" ref={volumeRef}>
      <button 
        onClick={toggleVolumeSlider} 
        className="transparent circle"
        aria-label="Volume Control"
        aria-haspopup="true"
        aria-expanded={showVolumeSlider}
      >
        <i className={`fa-solid ${getVolumeIcon()} amber-text`}></i>
      </button>
      
      {showVolumeSlider && (
        <div className="menu volume-menu">
          <div className="item">
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={volume} 
              onChange={handleVolumeChange} 
              className="volume-slider" 
              style={{ width: '100%', margin: '8px 0' }}
            />
            <div className="text-center">{volume}%</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VolumeControl;