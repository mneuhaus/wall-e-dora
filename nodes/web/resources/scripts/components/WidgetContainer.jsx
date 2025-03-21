import React, { useState, memo } from 'react';
import { useGridContext } from '../contexts/GridContext';
import { WIDGET_TYPES } from '../constants/widgetTypes';
import { getWidgetComponent, hasWidgetSettings } from './widgets';
import { migrateWidgetType } from '../utils/widgetMigration';

// Memoized modal component to prevent re-renders
const WidgetSettingsModal = memo(({ onClose, componentProps, type, title }) => {
  // Get the component for this widget type
  const SettingsComponent = getWidgetComponent(type);
  
  if (!SettingsComponent || SettingsComponent === 'div') {
    return null; // No settings component for this widget type
  }
  
  console.log(`Opening settings modal for ${type} with props:`, componentProps);
  
  return (
    <div className="modal active global-modal" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h5>{title || 'Widget Settings'}</h5>
          <button onClick={onClose} className="btn-close">×</button>
        </div>
        <div className="modal-body">
          <SettingsComponent 
            {...componentProps} 
            inSettingsModal={true} 
            i={componentProps.i}
          />
        </div>
        <div className="modal-footer">
          <button onClick={onClose} className="btn-flat">Close</button>
        </div>
      </div>
    </div>
  );
});

const WidgetContainer = ({ type, widgetProps }) => {
  const { isEditable, removeWidget } = useGridContext();
  const [showSettings, setShowSettings] = useState(false);
  
  // Migrate legacy widget types to new format
  const migratedType = migrateWidgetType(type);
  
  // Get the component from the widget registry
  let Component = getWidgetComponent(migratedType);
  let isUnknownType = false;
  
  if (!Component) {
    console.warn(`Unknown widget type: "${migratedType}", falling back to default div`);
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
    
    switch (migratedType) {
      case WIDGET_TYPES.SERVO: {
        const servoId = widgetProps.servoId;
        if (servoId === undefined || servoId === null) {
          return 'Servo (unassigned)';
        }
        return `Servo ${servoId}`;
      }
      case WIDGET_TYPES.JOYSTICK: {
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
      case WIDGET_TYPES.SEPARATOR:
        return 'Separator';
      case WIDGET_TYPES.TEST:
        return 'Test Widget';
      case WIDGET_TYPES.SOUND:
        return 'Available Sounds';
      default:
        return `Widget (${migratedType})`;
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
      {isEditable && (
        <div className="widget-badges">
          <button className="widget-badge drag-handle">
            <i className="fas fa-grip-horizontal"></i>
          </button>
          {hasWidgetSettings(migratedType) && (
            <button onClick={openSettings} className="widget-badge settings">
              <i className="fas fa-cog"></i>
            </button>
          )}
          <button onClick={handleRemove} className="widget-badge remove">
            <i className="fas fa-times"></i>
          </button>
        </div>
      )}
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
      
      {/* Global Settings Modal - rendered at body level for positioning */}
      {showSettings && hasWidgetSettings(migratedType) && (
        <WidgetSettingsModal
          onClose={closeSettings}
          componentProps={componentProps}
          type={migratedType}
          title={getWidgetTitle() + " Settings"}
        />
      )}
      
      {/* Extracted to a separate component to prevent re-rendering */}
    </div>
  );
};

export default WidgetContainer;