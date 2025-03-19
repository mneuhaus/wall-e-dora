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
import ConnectionStatus from './components/ConnectionStatus';
import GridLock from './components/GridLock';
import AddWidget from './components/AddWidget';
import Power from './components/Power';
import Volume from './components/Volume';
import ServoStatus from './components/ServoStatus';
import Gamepad from './components/Gamepad';

// Import views
import Dashboard from './views/Dashboard';
import GamepadView from './views/Gamepad';
import ServoDebug from './views/ServoDebug';

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
          <header style={{ flex: '0 0 auto' }}>
            <nav>
              <Link className="top-app-bar__title" style={{ fontSize: '20px', alignItems: 'left' }} to="/">wall-e</Link>
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