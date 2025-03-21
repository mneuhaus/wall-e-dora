# Wall-E Web UI - React Frontend

This is the React-based frontend for the Wall-E robot control system. The application provides a dashboard with drag-and-drop widgets for controlling servos, playing sounds, and viewing robot status.

## Technology Stack

- **React**: UI library for building component-based interfaces
- **React Router**: For handling navigation and URL routing
- **React Grid Layout**: Drag and drop grid system for the dashboard
- **BeerCSS**: CSS framework with amber theme
- **WebSocket**: Real-time communication with the backend
- **localStorage**: Browser persistence for grid layout

## Installation

```bash
# Install dependencies
pnpm install

# Start development server with hot reloading
pnpm run watch

# Build for production
pnpm run build
```

## Architecture

### State Management

The application uses React's Context API for state management:

- **AppContext**: Global application state (servos, connection status)
- **GridContext**: Dashboard grid layout and widget management

### Components Structure

- **Views/**
  - DashboardView.jsx: Main dashboard with grid layout
  - GamepadView.jsx: Gamepad controller interface
  - ServoDebugView.jsx: Detailed servo debugging

- **Components/**
  - `/widgets/`: Grid-based draggable components
  - `/status/`: Status indicator components
  - `/controls/`: User input control components
  - `/common/`: Shared utility components

### Communication

The application communicates with the backend using WebSockets:

- **Node.js**: WebSocket client for sending and receiving events
- Event-based communication using a pub/sub pattern

### Grid Layout Persistence

Dashboard widgets and their layouts are saved automatically to:

- **Backend**: For cross-device global persistence (primary storage)
- **localStorage**: For client-side fallback when offline

The backend persistence ensures that:
- Widget layouts are synchronized across all devices
- Changes made on one device are reflected on all other devices
- Widget positioning is consistent throughout the entire robot control ecosystem
- Layout changes persist even when accessing from different browsers or devices

localStorage serves as a fallback mechanism when:
- The backend connection is temporarily unavailable
- The backend has no saved state yet

To reset the grid layout for all devices:
1. Enter edit mode by clicking the lock icon
2. Click the trash icon that appears next to it
3. Confirm the reset in the dialog (note that this will affect all devices)

## Frontend Testing

The frontend tests use Jest and React Testing Library to test components without requiring a running Dora server.

### Running Tests

```bash
# Install test dependencies
pnpm install

# Run all tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run tests with coverage report
pnpm test:coverage
```

### Test Structure

- Tests are located in `__tests__` directories next to the components they test
- Mock implementations are in `__mocks__` directories
- The test setup is in `test-setup.js`

### Mocking Strategy

The tests use mocks to avoid dependence on the actual Dora server:

1. **Node.js Service**: The WebSocket communication service is mocked to simulate events
2. **Context Providers**: React contexts are mocked to provide test data
3. **Components**: External components like sliders are mocked for easier testing

### Writing New Tests

To write a new test:

1. Create a `__tests__` directory next to the component you want to test
2. Create a test file named `ComponentName.test.jsx`
3. Import the component and any required mocks
4. Render the component with necessary providers
5. Simulate user interactions using React Testing Library
6. Assert expected outcomes

Example:

```jsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MyComponent from '../MyComponent';
import { AppProvider } from '../../../contexts/AppContext';

describe('MyComponent', () => {
  test('renders correctly', () => {
    render(
      <AppProvider>
        <MyComponent />
      </AppProvider>
    );
    
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

## Adding New Widgets

To add a new widget type:

1. Create a new component in `components/widgets/`
2. Add it to the widget registry in `components/widgets/index.js`
3. Add a constant for the widget type in `constants/widgetTypes.js` 
4. Update the AddWidget dialog to include your new widget type

## Theme Customization

The UI follows the BeerCSS amber theme. Theme variables:

- `--primary`: Amber primary color
- `--surface`: Background surface color
- `--text`: Text color