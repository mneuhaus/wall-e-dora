import React, { useState, useEffect } from 'react';
import node from '../../Node';

/**
 * EyesWidget - A grid widget for displaying and controlling WALL-E eye displays
 * 
 * Displays a gallery of GIF and JPG images for eye displays
 * 
 * @component
 */
const EyesWidget = (props) => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);
  
  // Listen for available images
  useEffect(() => {
    // Listen for images list
    const unsubscribe = node.on('available_images', (event) => {
      console.log('Received images:', event);
      setImages(event.value || []);
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
  
  const formatImageName = (filename) => {
    // Remove file extension and convert special characters to spaces
    return filename
      .replace(/\.(gif|jpg|jpeg)$/i, '')
      .replace(/[-_]/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  const handleImageSelect = (image) => {
    setSelectedImage(image.filename);
    
    // Use the node event system to send play_gif event to the eyes node
    console.log(`Sending play_gif event with filename: ${image.filename}`);
    
    // Emit the play_gif event with the filename
    node.emit('play_gif', [image.filename]);
    
    // Visual feedback for selection
    setTimeout(() => {
      setSelectedImage(null);
    }, 2000);
  };

  // Custom styles for the GIF gallery
  const styles = `
    .gif-gallery-container {
      width: 100%;
      height: 100%;
      overflow-y: auto;
      padding: 10px;
    }
    
    .gif-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }
    
    .gif-item {
      cursor: pointer;
      border-radius: 8px;
      overflow: hidden;
      position: relative;
      aspect-ratio: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: transform 0.2s;
      background-color: rgba(255, 191, 0, 0.1);
      border: 1px solid rgba(255, 191, 0, 0.2);
    }
    
    .gif-item:hover {
      transform: scale(1.05);
      border-color: rgba(255, 191, 0, 0.5);
    }
    
    .gif-item.selected {
      border-color: rgba(255, 191, 0, 1);
      box-shadow: 0 0 8px rgba(255, 191, 0, 0.8);
    }
    
    .gif-thumbnail {
      width: 100%;
      height: 90%;
      object-fit: cover;
      object-position: center;
    }
    
    .gif-thumbnail img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    
    .gif-name {
      font-size: 0.8rem;
      margin-top: 5px;
      text-align: center;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      width: 100%;
      padding: 0 5px;
    }
    
    .empty-state {
      width: 100%;
      text-align: center;
      padding: 20px;
      color: rgba(255, 255, 255, 0.7);
    }
    
    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px;
      gap: 10px;
      color: rgba(255, 255, 255, 0.7);
    }
    
    .loading-state i {
      font-size: 2rem;
      color: rgba(255, 191, 0, 0.7);
    }
  `;
  
  // Render loading state
  if (loading) {
    return (
      <div className="loading-state">
        <style>{styles}</style>
        <i className="fas fa-spinner fa-spin"></i>
        <span>Loading images...</span>
      </div>
    );
  }
  
  return (
    <div className="gif-gallery-container">
      <style>{styles}</style>
      <h4 style={{ margin: '0 0 10px 0' }}>WALL-E Eyes</h4>
      
      {images.length > 0 ? (
        <div className="gif-grid">
          {images.map(image => (
            <div 
              key={image.filename}
              onClick={() => handleImageSelect(image)}
              className={`gif-item ${selectedImage === image.filename ? 'selected' : ''}`}
              role="button"
              tabIndex={0}
              onKeyPress={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  handleImageSelect(image);
                }
              }}
            >
              <div className="gif-thumbnail">
                <img 
                  src={`https://${window.location.hostname}:8443/get-image?path=${encodeURIComponent(image.source_path)}`}
                  alt={image.filename}
                  loading="lazy"
                />
              </div>
              <span className="gif-name">{formatImageName(image.filename)}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">No images available</div>
      )}
    </div>
  );
};

export default EyesWidget;