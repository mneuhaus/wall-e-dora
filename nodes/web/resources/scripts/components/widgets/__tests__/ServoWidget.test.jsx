import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import ServoWidget from '../ServoWidget';
import { AppProvider } from '../../../contexts/AppContext';
import { GridProvider } from '../../../contexts/GridContext';
import node from '../../../Node';

// Mock servo data for tests
const mockAvailableServos = [
  { id: 1, position: 90, min_pos: 0, max_pos: 180, speed: 50, alias: 'Head Servo' },
  { id: 2, position: 45, min_pos: 10, max_pos: 170, speed: 100, alias: 'Arm Servo' }
];

// Wrap component in required providers for testing
const renderWithProviders = (ui, { editable = false } = {}) => {
  return render(
    <AppProvider>
      <GridProvider initialEditable={editable}>
        {ui}
      </GridProvider>
    </AppProvider>
  );
};

describe('ServoWidget', () => {
  beforeEach(() => {
    // Clear mocks and set up initial state
    node.__clearMocks();
  });

  test('renders servo widget with correct position', async () => {
    // Render the widget
    renderWithProviders(<ServoWidget servoId={1} />);
    
    // Trigger servo_status event with mock data
    act(() => {
      node.__triggerEvent('servo_status', { value: mockAvailableServos });
    });
    
    // Check if slider is rendered with correct value
    expect(screen.getByTestId('mock-slider')).toHaveAttribute('data-value', '90');
  });

  test('updates position when servo status changes', async () => {
    // Render the widget
    renderWithProviders(<ServoWidget servoId={1} />);
    
    // Trigger initial servo_status
    act(() => {
      node.__triggerEvent('servo_status', { value: mockAvailableServos });
    });
    
    // Check initial position
    expect(screen.getByTestId('mock-slider')).toHaveAttribute('data-value', '90');
    
    // Update servo position with a new status event
    const updatedServos = [
      { ...mockAvailableServos[0], position: 120 },
      mockAvailableServos[1]
    ];
    
    act(() => {
      node.__triggerEvent('servo_status', { value: updatedServos });
    });
    
    // Check updated position
    expect(screen.getByTestId('mock-slider')).toHaveAttribute('data-value', '120');
  });

  test('emits set_servo event when position changes', async () => {
    // Render the widget
    renderWithProviders(<ServoWidget servoId={1} />);
    
    // Trigger servo_status event with mock data
    act(() => {
      node.__triggerEvent('servo_status', { value: mockAvailableServos });
    });
    
    // Find the slider and change its value
    const slider = screen.getByTestId('mock-slider');
    fireEvent.click(slider); // This will call the onChange with value+10
    
    // Check if set_servo was called with the right parameters
    expect(node.emit).toHaveBeenCalledWith('set_servo', [1, 100, 50]);
  });

  test('displays position value when in edit mode', async () => {
    // Render the widget in edit mode
    renderWithProviders(<ServoWidget servoId={1} />, { editable: true });
    
    // Trigger servo_status event with mock data
    act(() => {
      node.__triggerEvent('servo_status', { value: mockAvailableServos });
    });
    
    // Check if slider displays the correct value
    expect(screen.getByTestId('mock-slider')).toHaveAttribute('data-value', '90');
    
    // Check if position display text is in the rendered output
    expect(screen.getByText(/90/)).toBeInTheDocument();
  });

  test('does not display position value when not in edit mode', async () => {
    // Render the widget not in edit mode
    renderWithProviders(<ServoWidget servoId={1} />, { editable: false });
    
    // Trigger servo_status event with mock data
    act(() => {
      node.__triggerEvent('servo_status', { value: mockAvailableServos });
    });
    
    // Position display should not be visible
    expect(screen.queryByText('90')).not.toBeInTheDocument();
  });
});