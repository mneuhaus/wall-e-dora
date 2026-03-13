/**
 * DashboardView Component
 *
 * Main dashboard showing eyes and sounds only.
 *
 * @component
 */
import React, { useEffect, forwardRef } from 'react';
import node from '../Node';
import EyesWidget from '../components/widgets/EyesWidget';
import SoundWidget from '../components/widgets/SoundWidget';

const DashboardView = forwardRef((props, ref) => {
  useEffect(() => {
    node.emit('scan_sounds', []);
    node.emit('list_images', []);
  }, []);

  const styles = `
    .dashboard-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(120px, 34%);
      gap: 10px;
      width: 100%;
      height: 100%;
      overflow: hidden;
      padding: 10px;
      box-sizing: border-box;
    }

    @media (max-width: 720px) {
      .dashboard-grid {
        grid-template-columns: minmax(0, 58%) minmax(0, 42%);
        gap: 8px;
        padding: 8px;
      }
    }

    .dashboard-panel {
      min-width: 0;
      min-height: 0;
      height: 100%;
      overflow: hidden;
    }
  `;

  return (
    <div className="dashboard-view" ref={ref} style={{ height: '100%', overflow: 'hidden' }}>
      <style>{styles}</style>
      <div className="dashboard-grid">
        <div className="dashboard-panel">
          <EyesWidget />
        </div>
        <div className="dashboard-panel">
          <SoundWidget />
        </div>
      </div>
    </div>
  );
});

export default DashboardView;
