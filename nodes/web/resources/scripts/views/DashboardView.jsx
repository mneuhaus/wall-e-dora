/**
 * DashboardView Component
 * 
 * The main dashboard view that displays the grid of widgets.
 * Provides a responsive grid layout where widgets can be arranged, resized, and configured.
 * 
 * @component
 */
import React, { useEffect, forwardRef } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import { useAppContext } from '../contexts/AppContext';
import { useGridContext } from '../contexts/GridContext';
import WidgetContainer from '../components/WidgetContainer';
import node from '../Node';

const ResponsiveGridLayout = WidthProvider(Responsive);

const DashboardView = forwardRef((props, ref) => {
  const { availableServos } = useAppContext();
  const { 
    layout, 
    isEditable, 
    onLayoutChange
  } = useGridContext();

  // Request initial servo status
  useEffect(() => {
    // Request initial servo status
    node.emit('SCAN', []);
    
    // Note: Widget state loading is now fully handled by GridContext
  }, []);

  return (
    <div className="dashboard" ref={ref} style={{ height: '100%', overflow: 'auto' }}>
      <div className="grid-container" style={{ height: '100%', overflow: 'auto' }}>
        <ResponsiveGridLayout
          className="layout"
          layouts={{ lg: layout }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 24, md: 20, sm: 16, xs: 12, xxs: 8 }}
          rowHeight={40}
          isDraggable={isEditable}
          isResizable={isEditable}
          draggableHandle=".drag-handle"
          onLayoutChange={(layout) => onLayoutChange(layout)}
          margin={[5, 15]}
          useCSSTransforms={true}
          compactType="horizontal"
        >
          {layout.map(item => (
            <div key={item.i} data-grid={item}>
              <WidgetContainer 
                type={item.type}
                widgetProps={item}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      </div>
    </div>
  );
});

export default DashboardView;

// CSS is now in the main.css file, converted from the Vue component's scoped CSS