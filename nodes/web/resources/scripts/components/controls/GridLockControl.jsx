/**
 * GridLockControl Component
 * 
 * Controls for locking/unlocking the grid layout and resetting it.
 * When the grid is unlocked, widgets can be moved, resized, and deleted.
 * Provides a reset option to clear all widgets from the layout.
 * 
 * @component
 */
import React from 'react';
import { Group, ActionIcon, Tooltip } from '@mantine/core';
import { useGridContext } from '../../contexts/GridContext';

const GridLockControl = () => {
  const { isEditable, toggleGridEditing, resetGridLayout } = useGridContext();
  
  const handleResetGrid = (e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to reset the grid layout? This will clear all widgets for all devices.')) {
      resetGridLayout();
      console.log('Grid layout reset globally. All devices will be affected.');
    }
  };
  
  return (
    <Group gap="xs">
      <Tooltip 
        label={isEditable ? "Lock grid (exit edit mode)" : "Unlock grid (enter edit mode)"} 
        position="bottom"
        withArrow
      >
        <ActionIcon
          variant="transparent"
          radius="xl"
          onClick={toggleGridEditing}
          color={isEditable ? "green" : "amber"}
        >
          <i className={`fa-solid ${isEditable ? 'fa-lock-open' : 'fa-lock'}`}></i>
        </ActionIcon>
      </Tooltip>
      
      {isEditable && (
        <Tooltip 
          label="Reset grid layout for all devices" 
          position="bottom"
          withArrow
          color="red"
        >
          <ActionIcon
            variant="transparent"
            radius="xl"
            onClick={handleResetGrid}
            color="red"
          >
            <i className="fa-solid fa-trash"></i>
          </ActionIcon>
        </Tooltip>
      )}
    </Group>
  );
};

export default GridLockControl;