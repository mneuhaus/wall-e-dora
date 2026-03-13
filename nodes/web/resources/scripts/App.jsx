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
  FaceTrackingStatus,
} from './components/status';
import {
  VolumeControl as Volume,
  RandomSoundControl as RandomSound,
} from './components/controls';
import { GamepadStatus as Gamepad } from './components/status';

const Power = PowerStatus;
import {
  DashboardView as Dashboard,
  GalleryView,
  GamepadView,
  ServoDebugView as ServoDebug,
  ServoDiagnosticsOverviewView as ServoDiagnosticsOverview,
  ShowtimeView,
} from './views';

const TopNav = () => {
  const location = useLocation();

  const navItems = [
    { to: '/', label: 'Home', active: location.pathname === '/' },
    { to: '/showtime', label: 'Showtime', active: location.pathname.startsWith('/showtime') },
    { to: '/gallery', label: 'Gallery', active: location.pathname.startsWith('/gallery') },
  ];

  return (
    <Group gap={2} wrap="nowrap">
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
            padding: `${rem(4)} ${rem(6)}`,
            fontSize: rem(11),
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

const CameraBackground = ({ enabled, faceTrackingState }) => {
  const [useSnapshotFallback, setUseSnapshotFallback] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setUseSnapshotFallback(false);
    }
  }, [enabled]);

  const frameUrl = useSnapshotFallback
    ? `/camera/snapshot.jpg${faceTrackingState?.enabled ? '?annotated=1&' : '?'}t=${Date.now()}`
    : `/camera/stream.mjpeg${faceTrackingState?.enabled ? '?annotated=1' : ''}`;

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
      {enabled ? (
        <Box
          style={{
            position: 'absolute',
            inset: 0,
            transform: 'scale(1.015)',
            transformOrigin: 'center center',
          }}
        >
          <img
            src={frameUrl}
            alt=""
            onError={() => {
              if (!useSnapshotFallback) {
                setUseSnapshotFallback(true);
              }
            }}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: 'center',
            }}
          />
        </Box>
      ) : null}
      <Box
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.015) 0%, rgba(6, 8, 12, 0.05) 100%)',
        }}
      />
    </Box>
  );
};

const AppFrame = () => {
  const { cameraBackgroundEnabled, photoCaptureFlashToken, faceTrackingState } = useAppContext();

  const appStyles = `
    .camera-app {
      min-height: 100vh;
      background: #050608;
    }

    .camera-app.camera-live .sequence-bar__btn {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.16);
      box-shadow: 0 6px 18px rgba(0, 0, 0, 0.10);
      backdrop-filter: blur(4px);
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.92), 0 0 12px rgba(0, 0, 0, 0.45);
    }

    .camera-app.camera-live .sound-item {
      background: rgba(255, 255, 255, 0.16);
      border: 1px solid rgba(255, 255, 255, 0.22);
      box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
      backdrop-filter: blur(6px);
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.92), 0 0 12px rgba(0, 0, 0, 0.45);
    }

    .camera-app.camera-live .gif-item {
      background: rgba(255, 255, 255, 0.14);
      backdrop-filter: blur(4px);
      box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
    }

    .photo-capture-flash {
      position: fixed;
      inset: 0;
      z-index: 4;
      pointer-events: none;
      animation: photo-capture-flash 480ms ease-out forwards;
    }

    .photo-capture-flash::before {
      content: '';
      position: absolute;
      inset: 4px;
      border-radius: 18px;
      border: 2px solid rgba(255, 255, 255, 0.96);
      box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.28), 0 0 22px rgba(255, 255, 255, 0.95);
    }

    .photo-capture-flash::after {
      content: '';
      position: absolute;
      inset: 0;
      background: rgba(255, 255, 255, 0.07);
    }

    @keyframes photo-capture-flash {
      0% {
        opacity: 0;
      }

      18% {
        opacity: 1;
      }

      100% {
        opacity: 0;
      }
    }
  `;

  return (
    <Box className={`camera-app ${cameraBackgroundEnabled ? 'camera-live' : ''}`}>
      <style>{appStyles}</style>
      <CameraBackground enabled={cameraBackgroundEnabled} faceTrackingState={faceTrackingState} />
      {photoCaptureFlashToken > 0 ? (
        <Box
          key={photoCaptureFlashToken}
          aria-hidden="true"
          className="photo-capture-flash"
        />
      ) : null}

      <Box style={{ position: 'relative', zIndex: 1 }}>
        <AppShell
          header={{ height: rem(45) }}
          padding={0}
          styles={{
            header: {
              background: cameraBackgroundEnabled ? 'rgba(8, 10, 14, 0.16)' : 'rgba(8, 10, 14, 0.94)',
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
              background: cameraBackgroundEnabled ? 'rgba(8, 10, 14, 0.0)' : 'transparent',
            },
          }}
        >
          <AppShell.Header>
            <Container fluid px="sm" h="100%">
              <Group h="100%" justify="space-between" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <TopNav />
                </Group>

                <Group gap={4} wrap="nowrap">
                  <Gamepad />
                  <CameraStatus />
                  <FaceTrackingStatus />
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
              <Route path="/gallery" element={<GalleryView />} />
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
