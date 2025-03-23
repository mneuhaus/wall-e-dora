/**
 * GridLockControl Component
 * 
 * Controls for managing the grid layout through a dropdown menu.
 * Provides options for locking/unlocking the grid, adding widgets, and resetting the layout.
 * When the grid is unlocked, widgets can be moved, resized, and deleted.
 * 
 * @component
 */
import React, { useState } from 'react';
import { 
  ActionIcon, 
  Menu, 
  Tooltip, 
  Text, 
  Modal, 
  Group, 
  Title, 
  Stack, 
  Button, 
  UnstyledButton, 
  List,
  Divider,
  ScrollArea,
  Box 
} from '@mantine/core';
import { useGridContext } from '../../contexts/GridContext';
import { useAppContext } from '../../contexts/AppContext';
import { WIDGET_TYPES } from '../../constants/widgetTypes';

const GridLockControl = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { isEditable, toggleGridEditing, resetGridLayout, addWidget } = useGridContext();
  const { availableServos } = useAppContext();
  
  const handleResetGrid = () => {
    if (window.confirm('Are you sure you want to reset the grid layout? This will clear all widgets for all devices.')) {
      resetGridLayout();
      console.log('Grid layout reset globally. All devices will be affected.');
    }
  };
  
  const handleOpenModal = () => setIsModalOpen(true);
  const handleCloseModal = () => setIsModalOpen(false);
  
  const handleAddWidget = (type, config = {}) => {
    addWidget(type, config);
    handleCloseModal();
  };
  
  const handleAddServoWidget = (servoId) => {
    handleAddWidget(WIDGET_TYPES.SERVO, { servoId });
  };
  
  return (
    <>
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
              <Menu.Item
                leftSection={<i className="fa-solid fa-plus" style={{ width: 14 }}></i>}
                onClick={handleOpenModal}
              >
                Add Widget
              </Menu.Item>
              
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
      
      <Modal
        opened={isModalOpen}
        onClose={handleCloseModal}
        title="Add Widget"
        centered
        size="lg"
        overlayProps={{
          opacity: 0.7,
          blur: 3
        }}
      >
        <ScrollArea h={400} offsetScrollbars>
          <Stack spacing="md">
            <Box>
              <Title order={5} c="amber" mb="xs">Basic Widgets</Title>
              <List spacing="xs">
                <List.Item
                  icon={
                    <i className="fas fa-cube" style={{ color: 'var(--mantine-color-amber-6)' }}></i>
                  }
                >
                  <UnstyledButton 
                    onClick={() => handleAddWidget(WIDGET_TYPES.TEST)}
                    w="100%"
                    style={{
                      padding: '8px',
                      borderRadius: '4px',
                      transition: 'background-color 0.2s',
                      '&:hover': {
                        backgroundColor: 'var(--mantine-color-dark-6)'
                      }
                    }}
                  >
                    <Text>Test Widget</Text>
                  </UnstyledButton>
                </List.Item>
                
                <List.Item
                  icon={
                    <i className="fas fa-volume-up" style={{ color: 'var(--mantine-color-amber-6)' }}></i>
                  }
                >
                  <UnstyledButton 
                    onClick={() => handleAddWidget(WIDGET_TYPES.SOUND)}
                    w="100%"
                    style={{
                      padding: '8px',
                      borderRadius: '4px',
                      transition: 'background-color 0.2s',
                      '&:hover': {
                        backgroundColor: 'var(--mantine-color-dark-6)'
                      }
                    }}
                  >
                    <Text>Sounds Widget</Text>
                  </UnstyledButton>
                </List.Item>
                
                <List.Item
                  icon={
                    <i className="fas fa-gamepad" style={{ color: 'var(--mantine-color-amber-6)' }}></i>
                  }
                >
                  <UnstyledButton 
                    onClick={() => handleAddWidget(WIDGET_TYPES.JOYSTICK)}
                    w="100%"
                    style={{
                      padding: '8px',
                      borderRadius: '4px',
                      transition: 'background-color 0.2s',
                      '&:hover': {
                        backgroundColor: 'var(--mantine-color-dark-6)'
                      }
                    }}
                  >
                    <Text>Joystick Control</Text>
                  </UnstyledButton>
                </List.Item>
              </List>
            </Box>
            
            {availableServos && availableServos.length > 0 && (
              <>
                <Divider />
                
                <Box>
                  <Title order={5} c="amber" mb="xs">Servo Controls</Title>
                  <List spacing="xs">
                    {availableServos.map(servo => (
                      <List.Item
                        key={servo.id}
                        icon={
                          <i className="fas fa-cog" style={{ color: 'var(--mantine-color-amber-6)' }}></i>
                        }
                      >
                        <UnstyledButton 
                          onClick={() => handleAddServoWidget(servo.id)}
                          w="100%"
                          style={{
                            padding: '8px',
                            borderRadius: '4px',
                            transition: 'background-color 0.2s',
                            '&:hover': {
                              backgroundColor: 'var(--mantine-color-dark-6)'
                            }
                          }}
                        >
                          <Text>Servo {servo.id} - {servo.description || 'No Description'}</Text>
                        </UnstyledButton>
                      </List.Item>
                    ))}
                  </List>
                </Box>
              </>
            )}
          </Stack>
        </ScrollArea>
        
        <Group justify="flex-end" mt="md">
          <Button variant="outline" onClick={handleCloseModal}>Close</Button>
        </Group>
      </Modal>
    </>
  );
};

export default GridLockControl;