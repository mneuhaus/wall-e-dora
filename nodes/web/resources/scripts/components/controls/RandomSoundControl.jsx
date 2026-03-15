import React, { useState, useEffect, useRef } from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import node from '../../Node';
import { useAppContext } from '../../contexts/AppContext';
import { controlStyles } from '../status/controls';

const AMBIENT_SEQUENCE_IDS = ['idle-listen', 'idle-peek', 'idle-fidget'];
const MIN_IDLE_DELAY_MS = 5000;
const MAX_IDLE_DELAY_MS = 10000;
const BUSY_RETRY_MIN_MS = 1800;
const BUSY_RETRY_MAX_MS = 2800;

const randomDelay = (minDelay, maxDelay) => (
  Math.floor(Math.random() * (maxDelay - minDelay + 1)) + minDelay
);

/**
 * RandomSoundControl - Ambient mode that keeps WALL-E subtly alive while idle.
 *
 * @component
 */
const RandomSoundControl = () => {
  const { emotionMode } = useAppContext();
  const [isActive, setIsActive] = useState(false);
  const [sounds, setSounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pulseEffect, setPulseEffect] = useState(false);

  const timeoutRef = useRef(null);
  const pulseTimeoutRef = useRef(null);
  const isActiveRef = useRef(false);
  const sequenceActiveRef = useRef(false);
  const emotionModeActive = Boolean(emotionMode && emotionMode !== 'neutral');
  const emotionModeActiveRef = useRef(emotionModeActive);

  const clearAmbientTimer = () => {
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  const triggerPulse = () => {
    setPulseEffect(true);
    if (pulseTimeoutRef.current) {
      window.clearTimeout(pulseTimeoutRef.current);
    }
    pulseTimeoutRef.current = window.setTimeout(() => {
      setPulseEffect(false);
      pulseTimeoutRef.current = null;
    }, 2200);
  };

  const scheduleAmbientAction = (minDelay = MIN_IDLE_DELAY_MS, maxDelay = MAX_IDLE_DELAY_MS) => {
    clearAmbientTimer();
    if (!isActiveRef.current) {
      return;
    }

    if (emotionModeActiveRef.current) {
      return;
    }

    const delay = randomDelay(minDelay, maxDelay);
    timeoutRef.current = window.setTimeout(() => {
      timeoutRef.current = null;

      if (!isActiveRef.current) {
        return;
      }

      if (emotionModeActiveRef.current) {
        return;
      }

      if (sequenceActiveRef.current) {
        scheduleAmbientAction(BUSY_RETRY_MIN_MS, BUSY_RETRY_MAX_MS);
        return;
      }

      const sequenceId = AMBIENT_SEQUENCE_IDS[
        Math.floor(Math.random() * AMBIENT_SEQUENCE_IDS.length)
      ];

      node.emit('sequence_trigger', [sequenceId], {}, { trackActivity: false });
      triggerPulse();
      scheduleAmbientAction();
    }, delay);
  };

  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  useEffect(() => {
    emotionModeActiveRef.current = emotionModeActive;
  }, [emotionModeActive]);

  useEffect(() => {
    if (!emotionModeActive) {
      return;
    }

    setIsActive(false);
    stopAmbientMode();
  }, [emotionModeActive]);

  useEffect(() => {
    const cachedSequenceState = node.getLastEvent?.('sequence_state');
    const cachedSequencePayload = Array.isArray(cachedSequenceState?.value)
      ? cachedSequenceState.value[0]
      : cachedSequenceState?.value;
    sequenceActiveRef.current = Boolean(cachedSequencePayload?.active);

    node.emit('scan_sounds', [], {}, { trackActivity: false });

    const unsubscribeSounds = node.on('available_sounds', (event) => {
      setSounds(event.value || []);
      setLoading(false);
    });

    const unsubscribeActivity = node.on('user_activity', () => {
      if (isActiveRef.current) {
        scheduleAmbientAction();
      }
    });

    const unsubscribeSequenceState = node.on('sequence_state', (event) => {
      const payload = Array.isArray(event?.value) ? event.value[0] : event?.value;
      sequenceActiveRef.current = Boolean(payload?.active);
    });

    const handleEmergencyStop = () => {
      setIsActive(false);
      stopAmbientMode();
    };

    window.addEventListener('emergency_stop_triggered', handleEmergencyStop);

    const timeout = window.setTimeout(() => {
      setLoading(false);
    }, 3000);

    return () => {
      unsubscribeSounds();
      unsubscribeActivity();
      unsubscribeSequenceState();
      window.removeEventListener('emergency_stop_triggered', handleEmergencyStop);
      clearAmbientTimer();
      if (pulseTimeoutRef.current) {
        window.clearTimeout(pulseTimeoutRef.current);
        pulseTimeoutRef.current = null;
      }
      window.clearTimeout(timeout);
      isActiveRef.current = false;
    };
  }, []);

  const stopAmbientMode = () => {
    isActiveRef.current = false;
    clearAmbientTimer();
    if (pulseTimeoutRef.current) {
      window.clearTimeout(pulseTimeoutRef.current);
      pulseTimeoutRef.current = null;
    }
    setPulseEffect(false);
  };

  const toggleActive = () => {
    if (emotionModeActive) {
      return;
    }

    const nextActive = !isActiveRef.current;
    setIsActive(nextActive);

    if (nextActive) {
      isActiveRef.current = true;
      scheduleAmbientAction();
    } else {
      stopAmbientMode();
    }
  };

  const isDisabled = loading || sounds.length === 0 || emotionModeActive;

  const styles = `
    @keyframes glow {
      0% {
        filter: drop-shadow(0 0 0 rgba(255, 191, 0, 0.8));
      }
      50% {
        filter: drop-shadow(0 0 7px rgba(255, 191, 0, 0.85));
      }
      100% {
        filter: drop-shadow(0 0 0 rgba(255, 191, 0, 0.8));
      }
    }
  `;

  return (
    <Tooltip
      label={
        emotionModeActive
          ? 'Emotionsmodus aktiv'
          : isActive
            ? 'Zufallsmodus aus'
            : 'Zufallsmodus an'
      }
      withArrow
      position="bottom"
    >
      <div style={{ position: 'relative' }}>
        <style>{styles}</style>
        <ActionIcon
          variant="subtle"
          color={isActive ? 'amber' : 'gray'}
          onClick={toggleActive}
          disabled={isDisabled}
          aria-label="Zufallsmodus umschalten"
          style={controlStyles.actionIcon}
        >
          <i
            className={`fas fa-shuffle ${isActive ? 'amber-text' : ''}`}
            style={{
              ...controlStyles.icon,
              animation: pulseEffect && isActive ? 'glow 1s ease-in-out' : 'none',
            }}
          ></i>
        </ActionIcon>
      </div>
    </Tooltip>
  );
};

export default RandomSoundControl;
