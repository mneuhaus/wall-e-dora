import React from 'react';
import { render, act } from '@testing-library/react';
import { AppProvider, useAppContext } from '../AppContext';
import node from '../../Node';

// Test component that uses the context
const TestConsumer = () => {
  const { availableServos, isConnected } = useAppContext();
  return (
    <div>
      <div data-testid="connection-status">
        {isConnected ? 'Connected' : 'Disconnected'}
      </div>
      <div data-testid="servo-count">
        {availableServos.length}
      </div>
      <ul>
        {availableServos.map(servo => (
          <li key={servo.id} data-testid={`servo-${servo.id}`}>
            {servo.id}: {servo.position}
          </li>
        ))}
      </ul>
    </div>
  );
};

describe('AppContext', () => {
  beforeEach(() => {
    // Clear any previous mock calls
    node.__clearMocks();
  });

  test('provides default values', () => {
    const { getByTestId } = render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );
    
    expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
    expect(getByTestId('servo-count')).toHaveTextContent('0');
  });

  test('updates connection status', () => {
    const { getByTestId } = render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );
    
    // Initially disconnected
    expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
    
    // Trigger connection event
    act(() => {
      node.__triggerEvent('connection', true);
    });
    
    expect(getByTestId('connection-status')).toHaveTextContent('Connected');
  });

  test('updates available servos', () => {
    const { getByTestId } = render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );
    
    // Initially no servos
    expect(getByTestId('servo-count')).toHaveTextContent('0');
    
    // Trigger servo_status event with mock data
    const mockServos = [
      { id: 1, position: 90 },
      { id: 2, position: 45 }
    ];
    
    act(() => {
      node.__triggerEvent('servo_status', { value: mockServos });
    });
    
    // Now we should have 2 servos
    expect(getByTestId('servo-count')).toHaveTextContent('2');
    expect(getByTestId('servo-1')).toHaveTextContent('1: 90');
    expect(getByTestId('servo-2')).toHaveTextContent('2: 45');
  });

  test('merges single-servo status payloads', () => {
    const { getByTestId } = render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );

    act(() => {
      node.__triggerEvent('servo_status', { value: { id: 7, position: 123 } });
    });

    expect(getByTestId('servo-count')).toHaveTextContent('1');
    expect(getByTestId('servo-7')).toHaveTextContent('7: 123');
  });

  test('filters malformed servo entries from list payloads', () => {
    const { getByTestId, queryByTestId } = render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );

    act(() => {
      node.__triggerEvent('servos_list', {
        value: [{ id: 1, position: 90 }, '[]', null, { position: 12 }],
      });
    });

    expect(getByTestId('servo-count')).toHaveTextContent('1');
    expect(getByTestId('servo-1')).toHaveTextContent('1: 90');
    expect(queryByTestId('servo-undefined')).not.toBeInTheDocument();
  });

  test('requests servo status on mount', () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );
    
    // Verify that SCAN was called
    expect(node.emit).toHaveBeenCalledWith('SCAN', []);
  });
});
