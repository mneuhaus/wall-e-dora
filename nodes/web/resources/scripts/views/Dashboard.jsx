import React, { useEffect, forwardRef } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import { useAppContext } from '../contexts/AppContext';
import { useGridContext } from '../contexts/GridContext';
import WidgetContainer from '../components/WidgetContainer';
import node from '../Node';

const ResponsiveGridLayout = WidthProvider(Responsive);

const Dashboard = forwardRef((props, ref) => {
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
    <div className="dashboard" ref={ref}>
      <div className="grid-container">
        <ResponsiveGridLayout
          className="layout"
          layouts={{ lg: layout }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={80}
          isDraggable={isEditable}
          isResizable={isEditable}
          onLayoutChange={(layout) => onLayoutChange(layout)}
          margin={[10, 10]}
          useCSSTransforms={true}
          compactType="vertical"
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

export default Dashboard;

// CSS is now in the main.css file, converted from the Vue component's scoped CSS