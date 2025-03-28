/**
 * App Component
 * 
 * Main application component that sets up the routing and layout structure.
 * Provides context provider for application state.
 * 
 * @component
 */
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

// Mantine components
import { 
  AppShell, 
  Header, 
  Group, 
  Title, 
  Box, 
  ActionIcon,
  Container,
  rem
} from '@mantine/core';

// Import components
import { ConnectionStatus, ServoStatus, PowerStatus } from './components/status';
import { 
  VolumeControl as Volume,
  RandomSoundControl as RandomSound
} from './components/controls';
import { GamepadStatus as Gamepad } from './components/status';

// Alias PowerStatus as Power for consistency
const Power = PowerStatus;

// Import views
import { DashboardView as Dashboard, GamepadView, ServoDebugView as ServoDebug } from './views';

const App = () => {
  const dashboardRef = useRef(null);
  
  return (
    <AppProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true
        }}
      >
        <AppShell
          header={{ height: rem(30) }}
          padding={0}
          styles={{
            main: {
              display: 'flex',
              flexDirection: 'column',
              overflow: 'auto',
              paddingTop: rem(35),
              paddingBottom: 0,
              paddingLeft: 0,
              paddingRight: 0,
              height: 'calc(100vh - 35px)'
            }
          }}
        >
          <AppShell.Header>
            <Container fluid px="xs" h="100%">
              <Group h="100%" justify="space-between" wrap="nowrap">
                <Box component={Link} to="/" style={{ textDecoration: 'none' }}>
                  <Title order={4} c="amber">wall-e</Title>
                </Box>
                
                <Group gap="xs" wrap="nowrap">
                  <Gamepad />
                  <ServoStatus />
                  <Volume />
                  <RandomSound />
                  <Power />
                  <ConnectionStatus />
                </Group>
              </Group>
            </Container>
          </AppShell.Header>
          
          <AppShell.Main>
            <Routes>
              <Route path="/" element={<Dashboard ref={dashboardRef} />} />
              <Route path="/gamepad/:index" element={<GamepadView />} />
              <Route path="/servo/:id" element={<ServoDebug />} />
            </Routes>
          </AppShell.Main>
        </AppShell>
      </Router>
    </AppProvider>
  );
};

export default App;