// Jest setup file
import '@testing-library/jest-dom';

// Mock Node.js service
jest.mock('./scripts/Node', () => {
  const mitt = require('mitt');
  
  // Create a mock emitter
  const emitter = mitt();
  
  // Create a mock Node instance
  const mockNode = {
    emitter,
    on: jest.fn((eventName, callback) => {
      emitter.on(eventName, callback);
      return () => emitter.off(eventName, callback);
    }),
    emit: jest.fn((outputId, data, metadata = {}) => {
      // Record the emit call but don't actually do anything
    }),
    // Expose methods to trigger events in tests
    __triggerEvent: (eventName, data) => {
      emitter.emit(eventName, data);
    },
    __clearMocks: () => {
      jest.clearAllMocks();
      // Clear all event listeners
      emitter.all.clear();
    }
  };
  
  // Make the mock available globally for tests
  global.mockNode = mockNode;
  
  return mockNode;
});

// Mock for rc-slider
jest.mock('rc-slider', () => {
  return jest.fn(props => {
    return (
      <div 
        data-testid="mock-slider"
        data-min={props.min}
        data-max={props.max}
        data-value={props.value}
        onClick={() => props.onChange && props.onChange(props.value + 10)}
      >
        Slider: {props.value}
      </div>
    );
  });
});

// Set up window globals that might be used
global.WebSocket = jest.fn(() => ({
  addEventListener: jest.fn(),
  close: jest.fn(),
  send: jest.fn(),
  readyState: 1, // OPEN
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3
}));

// Clear mocks between tests
beforeEach(() => {
  jest.clearAllMocks();
  
  // Clear any registered event listeners on the mock node
  if (global.mockNode && global.mockNode.__clearMocks) {
    global.mockNode.__clearMocks();
  }
});