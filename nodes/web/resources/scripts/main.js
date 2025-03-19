import "beercss";
import "material-dynamic-colors";
import '@fortawesome/fontawesome-free/css/all.css';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import '../styles/main.css';

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

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

// Initialize UI theme with BeerCSS
(async () => {
  try {
    let theme = await ui("theme", "#ffd700");
    console.log("Theme initialized:", theme);
  } catch (e) {
    console.warn("Could not initialize BeerCSS theme:", e);
  }
  
  // Mount React app
  const container = document.getElementById('root');
  const root = createRoot(container);
  root.render(<App />);
})();