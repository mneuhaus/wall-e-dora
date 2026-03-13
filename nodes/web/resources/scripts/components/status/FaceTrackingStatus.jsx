/**
 * FaceTrackingStatus Component
 *
 * Toggles simple face-follow mode for the head pivot.
 *
 * @component
 */
import React from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import { useAppContext } from '../../contexts/AppContext';
import { statusIconStyles } from './StatusIconStyles';

const FaceTrackingStatus = () => {
  const { faceTrackingState, toggleFaceTracking } = useAppContext();
  const {
    enabled,
    supported,
    face_detected: faceDetected,
    sequence_active: sequenceActive,
    error,
  } = faceTrackingState;

  let label = 'Gesichtstracking einschalten';
  if (!supported) {
    label = error || 'Gesichtstracking nicht verfuegbar';
  } else if (enabled && faceDetected) {
    label = sequenceActive ? 'Gesichtstracking aktiv, waehrend Szene pausiert' : 'Gesicht erkannt, Kopf folgt';
  } else if (enabled) {
    label = sequenceActive ? 'Gesichtstracking aktiv, waehrend Szene pausiert' : 'Gesichtstracking aktiv, schaut sich um';
  }

  const color = !supported
    ? 'var(--mantine-color-red-6)'
    : faceDetected
      ? 'var(--mantine-color-green-5)'
      : enabled
        ? 'var(--mantine-color-amber-5)'
        : 'var(--mantine-color-gray-6)';

  return (
    <Tooltip
      label={label}
      position="bottom"
      withArrow
    >
      <ActionIcon
        variant="transparent"
        radius="xl"
        aria-label="Gesichtstracking"
        style={statusIconStyles.actionIcon}
        onClick={() => {
          if (supported) {
            toggleFaceTracking();
          }
        }}
        disabled={!supported}
      >
        <i
          className="fa-solid fa-user"
          style={{
            color,
            ...statusIconStyles.icon,
          }}
        ></i>
      </ActionIcon>
    </Tooltip>
  );
};

export default FaceTrackingStatus;
