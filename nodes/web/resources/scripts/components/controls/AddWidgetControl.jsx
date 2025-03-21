/**
 * AddWidgetControl Component
 * 
 * A control for adding widgets to the dashboard grid.
 * Provides a modal dialog with different widget options.
 * 
 * @component
 */
import React, { useState } from 'react';
import { useGridContext } from '../../contexts/GridContext';
import { useAppContext } from '../../contexts/AppContext';
import { WIDGET_TYPES } from '../../constants/widgetTypes';

const AddWidgetControl = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { addWidget } = useGridContext();
  const { availableServos } = useAppContext();
  const { isEditable } = useGridContext();
  
  const openDialog = () => {
    setIsDialogOpen(true);
  };
  
  const closeDialog = () => {
    setIsDialogOpen(false);
  };
  
  const handleAddWidget = (type, config = {}) => {
    addWidget(type, config);
    closeDialog();
  };
  
  const handleAddServoWidget = (servoId) => {
    handleAddWidget(WIDGET_TYPES.SERVO, { servoId });
  };
  
  if (!isEditable) {
    return null;
  }
  
  return (
    <>
      <button onClick={openDialog} className="transparent circle">
        <i className="fa-solid fa-plus"></i>
      </button>
      
      {isDialogOpen && (
        <div className="modal active" style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center' 
        }}>
          <div className="modal-content">
            <div className="modal-header">
              <h5>Add Widget</h5>
              <button onClick={closeDialog} className="btn-close">×</button>
            </div>
            <div className="modal-body">
              <div className="widget-options">
                <div className="widget-category">
                  <h6 className="category-title amber-text">Basic Widgets</h6>
                  <ul className="widget-list">
                    <li onClick={() => handleAddWidget(WIDGET_TYPES.TEST)} className="widget-list-item">
                      <i className="fas fa-cube amber-text"></i>
                      <span>Test Widget</span>
                    </li>
                    <li onClick={() => handleAddWidget(WIDGET_TYPES.SOUND)} className="widget-list-item">
                      <i className="fas fa-volume-up amber-text"></i>
                      <span>Sounds Widget</span>
                    </li>
                    <li onClick={() => handleAddWidget(WIDGET_TYPES.JOYSTICK)} className="widget-list-item">
                      <i className="fas fa-gamepad amber-text"></i>
                      <span>Joystick Control</span>
                    </li>
                  </ul>
                </div>
                
                {availableServos && availableServos.length > 0 && (
                  <div className="widget-category">
                    <h6 className="category-title amber-text">Servo Controls</h6>
                    <ul className="widget-list">
                      {availableServos.map(servo => (
                        <li 
                          key={servo.id} 
                          onClick={() => handleAddServoWidget(servo.id)} 
                          className="widget-list-item"
                        >
                          <i className="fas fa-cog amber-text"></i>
                          <span>Servo {servo.id} - {servo.description || 'No Description'}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={closeDialog} className="btn-flat">Close</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AddWidgetControl;