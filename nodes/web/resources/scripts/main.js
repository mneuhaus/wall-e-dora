// Import Mantine styles
import '@mantine/core/styles.css';

// Other CSS imports
import '@fortawesome/fontawesome-free/css/all.css';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import 'rc-slider/assets/index.css';
import '../styles/main.css';

import React from 'react';
import { createRoot } from 'react-dom/client';
import { MantineProvider, createTheme } from '@mantine/core';
import App from './App.jsx';

// Create Mantine theme with amber as primary color
const theme = createTheme({
  primaryColor: 'amber',
  colors: {
    // Define amber color palette similar to BeerCSS amber
    amber: [
      '#FFF8E1', // 0
      '#FFECB3', // 1
      '#FFE082', // 2
      '#FFD54F', // 3
      '#FFCA28', // 4
      '#FFC107', // 5
      '#FFB300', // 6
      '#FFA000', // 7
      '#FF8F00', // 8
      '#FF6F00'  // 9
    ]
  }
});

// Make initial grid state available globally via a custom event
// This allows our context to access it before establishing WebSocket connection
document.addEventListener('DOMContentLoaded', () => {
  // gridState is injected by the server in template.html
  if (typeof window.gridState !== 'undefined') {
    // Dispatch a custom event with the grid state
    const event = new CustomEvent('grid_state_initialized', { 
      detail: window.gridState 
    });
    document.dispatchEvent(event);
  }
});

// Initialize the application
(() => {
  // Mount React app with Mantine Provider
  const container = document.getElementById('root');
  const root = createRoot(container);
  root.render(
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <App />
    </MantineProvider>
  );
})();