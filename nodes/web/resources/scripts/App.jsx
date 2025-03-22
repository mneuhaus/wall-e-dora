import React, { useRef } from 'react';
import { 
  HashRouter as Router, 
  Routes, 
  Route, 
  Link,
  createRoutesFromElements,
  createBrowserRouter, 
  RouterProvider 
} from 'react-router-dom';
import { UNSAFE_createBrowserHistory } from 'react-router-dom';
import { AppProvider } from './contexts/AppContext';
import { GridProvider } from './contexts/GridContext';

// Import components
import { ConnectionStatus, ServoStatus, PowerStatus } from './components/status';
import { GridLockControl as GridLock, AddWidgetControl as AddWidget, VolumeControl as Volume } from './components/controls';
import { GamepadStatus as Gamepad } from './components/status';

// Alias PowerStatus as Power
const Power = PowerStatus;

// Import views
import { DashboardView as Dashboard, GamepadView, ServoDebugView as ServoDebug } from './views';

const App = () => {
  const dashboardRef = useRef(null);
  
  return (
    <AppProvider>
      <GridProvider>
        <Router
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true
          }}
        >
          <header style={{ flex: '0 0 auto', overflow: 'visible', minBlockSize: '2.5rem' }}>
            <nav>
              <Link className="top-app-bar__title" style={{ alignItems: 'left' }} to="/">wall-e</Link>
              <div className="max">&nbsp;</div>
              <Gamepad />
              <ServoStatus />
              <Power />
              <Volume />
              <AddWidget />
              <GridLock />
              <ConnectionStatus />
            </nav>
          </header>
          
          <main style={{ flex: '1 1 auto', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Routes>
              <Route path="/" element={<Dashboard ref={dashboardRef} />} />
              <Route path="/gamepad/:index" element={<GamepadView />} />
              <Route path="/servo/:id" element={<ServoDebug />} />
            </Routes>
          </main>
        </Router>
      </GridProvider>
    </AppProvider>
  );
};

export default App;