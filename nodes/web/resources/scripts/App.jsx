/**
 * App Component
 *
 * Main application component that sets up the routing and layout structure.
 * Provides context provider for application state.
 *
 * @component
 */
import React, { useEffect, useState } from 'react';
import {
  HashRouter as Router,
  Routes,
  Route,
  Link,
  useLocation,
} from 'react-router-dom';
import { AppProvider, useAppContext } from './contexts/AppContext';

import {
  AppShell,
  Group,
  Title,
  Box,
  Container,
  rem,
} from '@mantine/core';

import {
  ConnectionStatus,
  ServoStatus,
  PowerStatus,
  DoorStatus,
  CameraStatus,
} from './components/status';
import {
  VolumeControl as Volume,
  RandomSoundControl as RandomSound,
} from './components/controls';
import { GamepadStatus as Gamepad } from './components/status';

const Power = PowerStatus;

import {
  DashboardView as Dashboard,
  GamepadView,
  ServoDebugView as ServoDebug,
  ServoDiagnosticsOverviewView as ServoDiagnosticsOverview,
  ShowtimeView,
} from './views';

const CAMERA_REFRESH_DELAY_MS = 450;
const CAMERA_RETRY_DELAY_MS = 1200;

const TopNav = () => {
  const location = useLocation();

  const navItems = [
    { to: '/', label: 'Home', active: location.pathname === '/' },
    { to: '/showtime', label: 'Showtime', active: location.pathname.startsWith('/showtime') },
  ];

  return (
    <Group gap={4} wrap="nowrap">
      {navItems.map((item) => (
        <Box
          key={item.to}
          component={Link}
          to={item.to}
          style={{
            textDecoration: 'none',
            color: item.active ? 'var(--mantine-color-amber-4)' : 'rgba(255, 255, 255, 0.72)',
            background: item.active ? 'rgba(255, 191, 0, 0.14)' : 'transparent',
            border: item.active ? '1px solid rgba(255, 191, 0, 0.28)' : '1px solid transparent',
            borderRadius: rem(999),
            padding: `${rem(4)} ${rem(9)}`,
            fontSize: rem(13),
            fontWeight: 700,
            lineHeight: 1,
            whiteSpace: 'nowrap',
          }}
        >
          {item.label}
        </Box>
      ))}
    </Group>
  );
};

const CameraBackground = ({ enabled }) => {
  const [frameUrl, setFrameUrl] = useState('');

  useEffect(() => {
    if (!enabled) {
      setFrameUrl('');
      return undefined;
    }

    let cancelled = false;
    let timeoutId = 0;

    const loadNextFrame = () => {
      const nextUrl = `/camera/snapshot.jpg?t=${Date.now()}`;
      const image = new Image();

      image.onload = () => {
        if (cancelled) {
          return;
        }
        setFrameUrl(nextUrl);
        timeoutId = window.setTimeout(loadNextFrame, CAMERA_REFRESH_DELAY_MS);
      };

      image.onerror = () => {
        if (cancelled) {
          return;
        }
        timeoutId = window.setTimeout(loadNextFrame, CAMERA_RETRY_DELAY_MS);
      };

      image.src = nextUrl;
    };

    loadNextFrame();

    return () => {
      cancelled = true;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [enabled]);

  return (
    <Box
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        opacity: enabled ? 1 : 0,
        transition: 'opacity 180ms ease',
        pointerEvents: 'none',
        overflow: 'hidden',
        background: '#050608',
      }}
    >
      {frameUrl ? (
        <img
          src={frameUrl}
          alt=""
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center',
            filter: 'brightness(1.26) saturate(1.05) contrast(1.04)',
            transform: 'scale(1.015)',
          }}
        />
      ) : null}
      <Box
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(6, 8, 12, 0.18) 100%)',
        }}
      />
    </Box>
  );
};

const AppFrame = () => {
  const { cameraBackgroundEnabled } = useAppContext();

  const appStyles = `
    .camera-app {
      min-height: 100vh;
      background: #050608;
    }

    .camera-app.camera-live .sequence-bar__btn,
    .camera-app.camera-live .sound-item {
      background: rgba(255, 255, 255, 0.14);
      border: 1px solid rgba(255, 255, 255, 0.18);
      box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
      backdrop-filter: blur(6px);
    }

    .camera-app.camera-live .gif-item {
      background: rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(4px);
      box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
    }
  `;

  return (
    <Box className={`camera-app ${cameraBackgroundEnabled ? 'camera-live' : ''}`}>
      <style>{appStyles}</style>
      <CameraBackground enabled={cameraBackgroundEnabled} />

      <Box style={{ position: 'relative', zIndex: 1 }}>
        <AppShell
          header={{ height: rem(45) }}
          padding={0}
          styles={{
            header: {
              background: cameraBackgroundEnabled ? 'rgba(8, 10, 14, 0.24)' : 'rgba(8, 10, 14, 0.94)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              backdropFilter: 'blur(12px)',
            },
            main: {
              display: 'flex',
              flexDirection: 'column',
              overflow: 'auto',
              paddingTop: rem(50),
              paddingBottom: 0,
              paddingLeft: 0,
              paddingRight: 0,
              height: 'calc(100vh - 50px)',
              background: cameraBackgroundEnabled ? 'rgba(8, 10, 14, 0.02)' : 'transparent',
            },
          }}
        >
          <AppShell.Header>
            <Container fluid px="sm" h="100%">
              <Group h="100%" justify="space-between" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <Box component={Link} to="/" style={{ textDecoration: 'none' }}>
                    <Title order={3} c="amber" style={{ fontSize: rem(22) }}>wall-e</Title>
                  </Box>
                  <TopNav />
                </Group>

                <Group gap="md" wrap="nowrap">
                  <Gamepad />
                  <CameraStatus />
                  <ServoStatus />
                  <DoorStatus />
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
              <Route path="/" element={<Dashboard />} />
              <Route path="/showtime" element={<ShowtimeView />} />
              <Route path="/gamepad/:index" element={<GamepadView />} />
              <Route path="/servo/:id" element={<ServoDebug />} />
              <Route path="/servos/diagnostics" element={<ServoDiagnosticsOverview />} />
            </Routes>
          </AppShell.Main>
        </AppShell>
      </Box>
    </Box>
  );
};

const App = () => {
  return (
    <AppProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AppFrame />
      </Router>
    </AppProvider>
  );
};

export default App;
