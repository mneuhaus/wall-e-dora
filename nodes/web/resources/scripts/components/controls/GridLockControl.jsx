/**
 * GridLockControl Component
 * 
 * Controls for managing the grid layout through a dropdown menu.
 * Provides options for locking/unlocking the grid and resetting the layout.
 * When the grid is unlocked, widgets can be moved, resized, and deleted.
 * 
 * @component
 */
import React from 'react';
import { ActionIcon, Menu, Tooltip, Text } from '@mantine/core';
import { useGridContext } from '../../contexts/GridContext';

const GridLockControl = () => {
  const { isEditable, toggleGridEditing, resetGridLayout } = useGridContext();
  
  const handleResetGrid = () => {
    if (window.confirm('Are you sure you want to reset the grid layout? This will clear all widgets for all devices.')) {
      resetGridLayout();
      console.log('Grid layout reset globally. All devices will be affected.');
    }
  };
  
  return (
    <Menu
      position="bottom-end"
      withArrow
      shadow="md"
      width={200}
    >
      <Menu.Target>
        <Tooltip 
          label="Grid controls" 
          position="bottom"
          withArrow
        >
          <ActionIcon
            variant="transparent"
            radius="xl"
            color={isEditable ? "green" : "amber"}
          >
            <i className="fa-solid fa-table-cells"></i>
          </ActionIcon>
        </Tooltip>
      </Menu.Target>
      
      <Menu.Dropdown>
        <Menu.Label>Grid Layout</Menu.Label>
        
        <Menu.Item
          leftSection={<i className={`fa-solid ${isEditable ? 'fa-lock' : 'fa-lock-open'}`} style={{ width: 14 }}></i>}
          onClick={toggleGridEditing}
          color={isEditable ? "amber" : "green"}
        >
          {isEditable ? "Lock Grid" : "Unlock Grid"}
        </Menu.Item>
        
        {isEditable && (
          <>
            <Menu.Divider />
            <Menu.Label>Danger Zone</Menu.Label>
            <Menu.Item
              leftSection={<i className="fa-solid fa-trash" style={{ width: 14 }}></i>}
              onClick={handleResetGrid}
              color="red"
            >
              Reset Layout
            </Menu.Item>
          </>
        )}
      </Menu.Dropdown>
    </Menu>
  );
};

export default GridLockControl;