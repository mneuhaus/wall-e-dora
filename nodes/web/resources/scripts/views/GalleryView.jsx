/**
 * GalleryView Component
 *
 * Shows saved camera photos from the robot.
 *
 * @component
 */
import React, { useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';

const formatCapturedAt = (value) => {
  if (!value) {
    return '';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const GalleryView = () => {
  const { photos, photosLoading, refreshPhotos } = useAppContext();

  useEffect(() => {
    refreshPhotos();
  }, []);

  const styles = `
    .gallery-view {
      min-height: 100%;
      overflow: auto;
      padding: 8px;
      box-sizing: border-box;
    }

    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .gallery-card {
      border-radius: 14px;
      overflow: hidden;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.10);
      box-shadow: 0 6px 18px rgba(0, 0, 0, 0.10);
      backdrop-filter: blur(4px);
    }

    .gallery-image {
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: cover;
      display: block;
      background: rgba(0,0,0,0.2);
    }

    .gallery-meta {
      padding: 7px 9px 8px;
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 0.74rem;
      color: rgba(255,255,255,0.86);
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.88), 0 0 10px rgba(0, 0, 0, 0.35);
    }

    .gallery-empty {
      padding: 18px 8px;
      color: rgba(255,255,255,0.8);
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.88), 0 0 10px rgba(0, 0, 0, 0.35);
    }
  `;

  return (
    <div className="gallery-view">
      <style>{styles}</style>

      {photosLoading && photos.length === 0 ? (
        <div className="gallery-empty">Lade Fotos...</div>
      ) : null}

      {!photosLoading && photos.length === 0 ? (
        <div className="gallery-empty">Noch keine Fotos gespeichert.</div>
      ) : null}

      {photos.length > 0 ? (
        <div className="gallery-grid">
          {photos.map((photo) => (
            <div
              key={photo.filename}
              className="gallery-card"
            >
              <img className="gallery-image" src={photo.url} alt={photo.filename} loading="lazy" />
              <div className="gallery-meta">
                <span>{formatCapturedAt(photo.captured_at)}</span>
                <span>{Math.max(1, Math.round((photo.size_bytes || 0) / 1024))} KB</span>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default GalleryView;
