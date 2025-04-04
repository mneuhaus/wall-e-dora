/**
 * ServoSelector Component
 * 
 * A dropdown selector component for choosing servos using Mantine components.
 * Displays available servos with their IDs and names.
 * Handles selection and provides the servo ID to the parent component.
 * 
 * @component
 */
import React, { useState, useEffect } from 'react';
import { useAppContext } from '../../../contexts/AppContext';
import { Select, Text, Group } from '@mantine/core';

const ServoSelector = ({ value, onChange, label }) => {
  const { availableServos } = useAppContext();
  const [selectedServo, setSelectedServo] = useState(null);
  const [options, setOptions] = useState([]);

  // Update options when availableServos changes
  useEffect(() => {
    const servoOptions = [
      { value: '', label: 'None Selected' }, // Option for no selection
      ...(availableServos || []).map(servo => ({
        value: String(servo.id), // Ensure value is string for Select component
        label: servo.alias ? `${servo.alias} (#${servo.id})` : `Servo #${servo.id}`,
        id: servo.id,
        alias: servo.alias
      }))
    ];
    setOptions(servoOptions);
    
    // Update selected servo info based on current value
    const currentSelectedValue = value === null ? '' : String(value);
    const foundServo = servoOptions.find(opt => opt.value === currentSelectedValue);
    setSelectedServo(foundServo || null);
    
  }, [availableServos, value]);

  const handleSelectChange = (selectedValue) => {
    // Find the selected option object
    const selectedOption = options.find(opt => opt.value === selectedValue);
    
    // Determine the ID to pass to onChange
    // If 'None Selected' is chosen, pass null
    // Otherwise, parse the ID from the value string
    const idToPass = selectedOption && selectedOption.value !== '' ? parseInt(selectedOption.value) : null;
    
    console.log(`ServoSelector selected: ${idToPass} (raw value: ${selectedValue})`);
    
    // Update local state for display
    setSelectedServo(selectedOption);
    
    // Call the parent onChange handler with the normalized ID (number or null)
    onChange(idToPass);
  };

  return (
    <Select
      label={label || 'Select Servo'}
      placeholder="Choose a servo"
      value={selectedServo ? selectedServo.value : ''} // Use empty string for 'None'
      onChange={handleSelectChange}
      data={options}
      searchable
      nothingFoundMessage="No servos available"
      styles={{
        input: { 
          backgroundColor: 'var(--mantine-color-dark-6)',
          borderColor: 'var(--mantine-color-dark-4)',
          '&:focus': {
            borderColor: 'var(--mantine-color-amber-6)'
          }
        },
        dropdown: {
          backgroundColor: 'var(--mantine-color-dark-7)',
          borderColor: 'var(--mantine-color-dark-4)'
        },
        item: {
          '&[data-selected]': {
            backgroundColor: 'var(--mantine-color-amber-9)',
            color: 'var(--mantine-color-dark-9)'
          },
          '&[data-hovered]': {
            backgroundColor: 'var(--mantine-color-dark-5)'
          }
        }
      }}
    />
  );
};

export default ServoSelector;
