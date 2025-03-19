import React, { useState } from 'react';
import node from '../Node';

const Volume = () => {
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);
  const [volume, setVolume] = useState(50);

  const toggleVolumeSlider = () => {
    setShowVolumeSlider(!showVolumeSlider);
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseInt(e.target.value);
    setVolume(newVolume);
    node.emit('set_volume', [newVolume]);
  };

  return (
    <div className="volume-control">
      <button onClick={toggleVolumeSlider} className="transparent circle">
        <i className="fa-solid fa-volume-high"></i>
      </button>
      
      {showVolumeSlider && (
        <div className="volume-slider-container">
          <input 
            type="range" 
            min="0" 
            max="100" 
            value={volume} 
            onChange={handleVolumeChange} 
            className="slider" 
          />
        </div>
      )}
    </div>
  );
};

export default Volume;