import React, { useState, useEffect } from 'react';
import { Select, Group, Tooltip, ActionIcon } from '@mantine/core';
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
  const [sortBy, setSortBy] = useState("filename");
  const [sortOrder, setSortOrder] = useState("asc");
  
  // Listen for available images
  useEffect(() => {
    // Listen for images list
    const unsubscribe = node.on('available_images', (event) => {
      console.log('Received images:', event);
      setImages(event.value || []);
      setLoading(false);
      
      // Update sort state from metadata if available
      if (event.metadata) {
        if (event.metadata.sort_by) {
          setSortBy(event.metadata.sort_by);
        }
        if (event.metadata.sort_order) {
          setSortOrder(event.metadata.sort_order);
        }
      }
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
  
  // Request images with the current sort settings
  const requestImages = () => {
    node.emit('list_images', [{ sort_by: sortBy, sort_order: sortOrder }]);
    setLoading(true);
  };
  
  // Update sorting when sortBy or sortOrder changes
  useEffect(() => {
    requestImages();
  }, [sortBy, sortOrder]);
  
  const formatImageName = (filename) => {
    // Remove file extension and convert special characters to spaces
    return filename
      .replace(/\.(gif|jpg|jpeg)$/i, '')
      .replace(/[-_]/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };
  
  // Format file size to KB or MB
  const formatFileSize = (bytes) => {
    if (bytes < 1024) {
      return bytes + ' B';
    } else if (bytes < 1024 * 1024) {
      return (bytes / 1024).toFixed(1) + ' KB';
    } else {
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
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
      padding: 8px;
      padding-right: 5px;
    }
    
    .sort-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      width: 100%;
    }
    
    .gif-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(65px, 1fr));
      gap: 10px;
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
    }
    
    .gif-item:hover {
      transform: scale(1.05);
    }
    
    .gif-item.selected {
      box-shadow: 0 0 8px rgba(255, 191, 0, 0.8);
    }
    
    .gif-thumbnail {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center;
      border-radius: 50%;
      overflow: hidden;
      position: relative;
    }
    
    .gif-thumbnail img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    
    .file-size {
      position: absolute;
      bottom: 0;
      right: 0;
      background-color: rgba(0, 0, 0, 0.7);
      color: white;
      font-size: 0.6rem;
      padding: 2px 4px;
      border-radius: 4px;
      z-index: 1;
    }
    
    
    .empty-state {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: center;
      padding: 20px;
      color: rgba(255, 255, 255, 0.7);
      font-size: 16px;
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
  
  // Toggle sort order (asc/desc)
  const toggleSortOrder = () => {
    setSortOrder(sortOrder === "asc" ? "desc" : "asc");
  };
  
  // Handle sort selection change
  const handleSortChange = (value) => {
    setSortBy(value);
  };
  
  return (
    <div className="gif-gallery-container">
      <style>{styles}</style>
      
      {images.length > 0 ? (
        <>
          <Group position="apart" mb="xs" align="center" className="sort-controls">
            <Select
              size="xs"
              value={sortBy}
              onChange={handleSortChange}
              data={[
                { value: 'filename', label: 'Name' },
                { value: 'size', label: 'Size' },
                { value: 'timestamp', label: 'Date' }
              ]}
              styles={{ 
                root: { flexGrow: 1, maxWidth: '120px' },
                input: { 
                  color: 'var(--mantine-color-white)',
                  backgroundColor: 'var(--mantine-color-dark-7)'
                }
              }}
            />
            <Tooltip 
              label={sortOrder === "asc" ? "Ascending order" : "Descending order"} 
              position="right"
            >
              <ActionIcon 
                size="sm" 
                variant="subtle"
                color="amber"
                onClick={toggleSortOrder}
              >
                <i className={`fas fa-sort-${sortOrder === "asc" ? "up" : "down"}`}></i>
              </ActionIcon>
            </Tooltip>
          </Group>
          
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
                <div className="file-size">{formatFileSize(image.size)}</div>
              </div>
            </div>
          ))}
          </div>
        </>
      ) : (
        <div className="empty-state">
          <i className="fas fa-image" style={{ marginRight: '10px', opacity: 0.5 }}></i>
          No images available
        </div>
      )}
    </div>
  );
};

export default EyesWidget;