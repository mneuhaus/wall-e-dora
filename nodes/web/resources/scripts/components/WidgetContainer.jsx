import React, { useState } from 'react';
import { useGridContext } from '../contexts/GridContext';

// Import widget components
import ServoControl from './ServoControl';
import TestWidget from './TestWidget';
import SoundsWidget from './SoundsWidget';
import JoystickControl from './JoystickControl';

const WidgetContainer = ({ type, widgetProps }) => {
  const { isEditable, removeWidget } = useGridContext();
  const [showSettings, setShowSettings] = useState(false);
  
  // Map widget types to components - be consistent with the type names
  const componentMap = {
    'servo-control': ServoControl,
    'separator': 'div',
    'test-widget': TestWidget,
    'sounds-widget': SoundsWidget,
    'joystick-control': JoystickControl
  };
  
  
  // Determine which component to render
  let Component = componentMap[type];
  let isUnknownType = false;
  
  if (!Component) {
    console.warn(`Unknown widget type: "${type}", falling back to default div`);
    Component = 'div';
    isUnknownType = true;
  }
  
  // Filter and transform props for the component
  const getComponentProps = () => {
    const filteredProps = { ...widgetProps };
    
    // Remove grid layout properties that shouldn't be passed to the component
    [
      // Grid positioning props
      'i', 'x', 'y', 'w', 'h', 'minW', 'minH', 'maxW', 'maxH', 'moved', 'static', 
      // Grid behavior props
      'isBounded', 'isDraggable', 'isResizable', 'resizeHandles',
      // Other react-grid-layout props that might cause issues
      'useCSSTransforms', 'transformScale', 'isDroppable', 'droppingItem',
      'placeholder', 'preventCollision', 'compactType', 'margin',
      'containerPadding', 'rowHeight', 'maxRows', 'cols',
      // Any other grid layout props
      'verticalCompact', 'layout', 'layouts', 'onLayoutChange', 'onDrag', 'onDragStart', 
      'onDragStop', 'onResize', 'onResizeStart', 'onResizeStop'
    ].forEach(prop => {
      delete filteredProps[prop];
    });
    
    return filteredProps;
  };
  
  // Get a title for the widget
  const getWidgetTitle = () => {
    
    switch (type) {
      case 'servo-control': {
        const servoId = widgetProps.servoId;
        if (servoId === undefined || servoId === null) {
          return 'Servo (unassigned)';
        }
        return `Servo ${servoId}`;
      }
      case 'joystick-control': {
        const xServoId = widgetProps.xServoId;
        const yServoId = widgetProps.yServoId;
        let title = 'Joystick';
        
        if (xServoId && yServoId) {
          title += ` (X: ${xServoId}, Y: ${yServoId})`;
        } else if (xServoId) {
          title += ` (X: ${xServoId})`;
        } else if (yServoId) {
          title += ` (Y: ${yServoId})`;
        } else {
          title += ' (unassigned)';
        }
        
        return title;
      }
      case 'separator':
        return 'Separator';
      case 'test-widget':
        return 'Test Widget';
      case 'sounds-widget':
        return 'Available Sounds';
      default:
        return `Widget (${type})`;
    }
  };
  
  const handleRemove = () => {
    removeWidget(widgetProps.i);
  };
  
  // Only pass standard props to the component - not handlers or layout props
  const componentProps = getComponentProps();
  
  const openSettings = () => {
    setShowSettings(true);
  };

  const closeSettings = () => {
    setShowSettings(false);
  };

  return (
    <div className="widget-container">
      <div className="widget-header">
        {isEditable && <div className="drag-handle"><i className="fas fa-grip-horizontal"></i></div>}
        <div className="widget-title">{getWidgetTitle()}</div>
        <div className="widget-actions">
          {(isEditable || type === 'joystick-control') && (
            <button onClick={openSettings} className="widget-settings-btn">
              <i className="fas fa-cog"></i>
            </button>
          )}
          {isEditable && (
            <button onClick={handleRemove} className="widget-remove-btn">
              <i className="fas fa-times"></i>
            </button>
          )}
        </div>
      </div>
      <div className="widget-content">
        {isUnknownType ? (
          <div className="widget-error">
            <i className="fas fa-exclamation-triangle"></i>
            <p>Unknown widget type: "{type}"</p>
            <small>This widget may need to be recreated.</small>
          </div>
        ) : (
          <Component {...componentProps} showSettings={showSettings} onCloseSettings={closeSettings} />
        )}
      </div>
      
      {/* Settings Modal */}
      {showSettings && type === 'joystick-control' && (
        <div className="modal active">
          <div className="modal-content">
            <div className="modal-header">
              <h5>Joystick Settings</h5>
              <button onClick={closeSettings} className="btn-close">×</button>
            </div>
            <div className="modal-body">
              {/* We'll pass the settings content as props to Component */}
              <Component {...componentProps} inSettingsModal={true} />
            </div>
            <div className="modal-footer">
              <button onClick={closeSettings} className="btn-flat">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WidgetContainer;