/**
 * AddWidgetControl Component
 * 
 * A control for adding widgets to the dashboard grid.
 * Provides a modal dialog with different widget options.
 * 
 * @component
 */
import React, { useState } from 'react';
import { 
  ActionIcon, 
  Modal, 
  Group, 
  Title, 
  Text, 
  Stack, 
  Button, 
  Paper, 
  UnstyledButton, 
  List,
  Divider,
  ScrollArea,
  Box
} from '@mantine/core';
import { useGridContext } from '../../contexts/GridContext';
import { useAppContext } from '../../contexts/AppContext';
import { WIDGET_TYPES } from '../../constants/widgetTypes';

const AddWidgetControl = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { addWidget } = useGridContext();
  const { availableServos } = useAppContext();
  const { isEditable } = useGridContext();
  
  const handleOpenModal = () => setIsModalOpen(true);
  const handleCloseModal = () => setIsModalOpen(false);
  
  const handleAddWidget = (type, config = {}) => {
    addWidget(type, config);
    handleCloseModal();
  };
  
  const handleAddServoWidget = (servoId) => {
    handleAddWidget(WIDGET_TYPES.SERVO, { servoId });
  };
  
  if (!isEditable) {
    return null;
  }
  
  return (
    <>
      <ActionIcon
        variant="transparent"
        radius="xl"
        onClick={handleOpenModal}
        aria-label="Add Widget"
      >
        <i className="fa-solid fa-plus"></i>
      </ActionIcon>
      
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

export default AddWidgetControl;