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
  - Dashboard.jsx: Main dashboard with grid layout
  - Gamepad.jsx: Gamepad controller interface
  - ServoDebug.jsx: Detailed servo debugging

- **Components/**
  - Core components (AddWidget, ConnectionStatus, etc.)
  - Widget components (SoundsWidget, ServoControl, etc.)

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

## Adding New Widgets

To add a new widget type:

1. Create a new component in `components/`
2. Add it to the component map in `WidgetContainer.jsx`
3. Update the AddWidget dialog to include your new widget type

## Theme Customization

The UI follows the BeerCSS amber theme. Theme variables:

- `--primary`: Amber primary color
- `--surface`: Background surface color
- `--text`: Text color