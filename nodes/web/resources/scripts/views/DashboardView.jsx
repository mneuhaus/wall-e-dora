/**
 * DashboardView Component
 * 
 * The main dashboard view that displays a fixed layout with eye and sound widgets.
 * Uses CSS Grid for reliable layout control.
 * 
 * @component
 */
import React, { useEffect, forwardRef } from 'react';
import { useAppContext } from '../contexts/AppContext';
import node from '../Node';
import EyesWidget from '../components/widgets/EyesWidget';
import SoundWidget from '../components/widgets/SoundWidget';

const DashboardView = forwardRef((props, ref) => {
  const { availableServos } = useAppContext();

  // Request initial servo status
  useEffect(() => {
    // Request initial servo status
    node.emit('SCAN', []);
    
    // Request sounds list
    node.emit('scan_sounds', []);
  }, []);

  // CSS Grid styles
  const styles = `
    .dashboard-grid {
      display: grid;
      grid-template-columns: 70% 30%;
      grid-template-rows: 1fr;
      grid-template-areas: 
        "eyes-content sounds-content";
      width: 100%;
      height: 100%;
      overflow: hidden;
    }
    
    .eyes-content {
      grid-area: eyes-content;
      padding: 10px;
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
    }
    
    .sounds-content {
      grid-area: sounds-content;
      padding: 10px;
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
      border-left: 1px solid rgba(255, 255, 255, 0.1);
    }
  `;

  return (
    <div className="dashboard" ref={ref} style={{ height: '100%', overflow: 'hidden' }}>
      <style>{styles}</style>
      <div className="dashboard-grid">
        <div className="eyes-content">
          <EyesWidget />
        </div>
        
        <div className="sounds-content">
          <SoundWidget />
        </div>
      </div>
    </div>
  );
});

export default DashboardView;