/**
 * App Component
 * 
 * Main application component that sets up the routing and layout structure.
 * Provides context providers for application state and grid management.
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
import { GridProvider } from './contexts/GridContext';

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
import { GridLockControl as GridLock, AddWidgetControl as AddWidget, VolumeControl as Volume } from './components/controls';
import { GamepadStatus as Gamepad } from './components/status';

// Alias PowerStatus as Power for consistency
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
          <AppShell
            header={{ height: rem(50) }}
            padding={0}
            styles={{
              main: {
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                paddingTop: rem(50),
                paddingBottom: 0,
                paddingLeft: 0,
                paddingRight: 0
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
                    <Power />
                    <Volume />
                    <AddWidget />
                    <GridLock />
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
      </GridProvider>
    </AppProvider>
  );
};

export default App;