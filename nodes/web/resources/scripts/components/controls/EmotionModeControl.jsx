import React, { useEffect, useRef } from 'react';
import node from '../../Node';
import { getEmotionMode, pickNextEmotionSequence } from '../../emotionModes';
import { useAppContext } from '../../contexts/AppContext';

const INITIAL_TRIGGER_MIN_MS = 650;
const INITIAL_TRIGGER_MAX_MS = 1400;
const USER_SETTLE_MIN_MS = 4500;
const USER_SETTLE_MAX_MS = 7000;
const BUSY_RETRY_MIN_MS = 1200;
const BUSY_RETRY_MAX_MS = 2200;

const randomDelay = (minDelay, maxDelay) => (
  Math.floor(Math.random() * (maxDelay - minDelay + 1)) + minDelay
);

function normalizeSequenceState(rawValue) {
  const payload = Array.isArray(rawValue) ? rawValue[0] : rawValue;
  return {
    active: Boolean(payload?.active),
    id: payload?.id || null,
  };
}

const EmotionModeControl = () => {
  const { emotionMode } = useAppContext();

  const modeRef = useRef(emotionMode);
  const sequenceActiveRef = useRef(false);
  const emotionSequenceActiveRef = useRef(false);
  const lastSequenceIdRef = useRef(null);
  const timerRef = useRef(null);
  const previousModeRef = useRef(emotionMode);

  const clearTimer = () => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const scheduleModeAction = (minDelay, maxDelay) => {
    clearTimer();

    const activeMode = modeRef.current;
    if (!activeMode || activeMode === 'neutral') {
      return;
    }

    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;

      const currentMode = modeRef.current;
      if (!currentMode || currentMode === 'neutral') {
        return;
      }

      if (sequenceActiveRef.current) {
        scheduleModeAction(BUSY_RETRY_MIN_MS, BUSY_RETRY_MAX_MS);
        return;
      }

      const idleForMs = Date.now() - node.getLastUserInteractionAt();
      if (idleForMs < USER_SETTLE_MIN_MS) {
        const remainingMs = USER_SETTLE_MIN_MS - idleForMs;
        scheduleModeAction(
          Math.max(BUSY_RETRY_MIN_MS, remainingMs + 300),
          Math.max(BUSY_RETRY_MAX_MS, remainingMs + 1200),
        );
        return;
      }

      const nextSequenceId = pickNextEmotionSequence(currentMode, lastSequenceIdRef.current);
      if (!nextSequenceId) {
        return;
      }

      lastSequenceIdRef.current = nextSequenceId;
      emotionSequenceActiveRef.current = true;
      node.emit('sequence_trigger', [nextSequenceId], {}, { trackActivity: false });

      const modeConfig = getEmotionMode(currentMode);
      scheduleModeAction(
        modeConfig.minDelayMs || USER_SETTLE_MIN_MS,
        modeConfig.maxDelayMs || USER_SETTLE_MAX_MS,
      );
    }, randomDelay(minDelay, maxDelay));
  };

  useEffect(() => {
    const cachedSequenceState = normalizeSequenceState(node.getLastEvent?.('sequence_state')?.value);
    sequenceActiveRef.current = cachedSequenceState.active;

    const unsubscribeSequenceState = node.on('sequence_state', (event) => {
      const nextState = normalizeSequenceState(event?.value);
      sequenceActiveRef.current = nextState.active;

      if (!nextState.active) {
        emotionSequenceActiveRef.current = false;
      }
    });

    const unsubscribeUserActivity = node.on('user_activity', () => {
      emotionSequenceActiveRef.current = false;

      if (modeRef.current && modeRef.current !== 'neutral') {
        scheduleModeAction(USER_SETTLE_MIN_MS, USER_SETTLE_MAX_MS);
      }
    });

    return () => {
      unsubscribeSequenceState();
      unsubscribeUserActivity();
      clearTimer();
    };
  }, []);

  useEffect(() => {
    const previousMode = previousModeRef.current;
    modeRef.current = emotionMode;
    clearTimer();

    if (!emotionMode || emotionMode === 'neutral') {
      lastSequenceIdRef.current = null;

      if (previousMode && previousMode !== 'neutral') {
        node.emit('sequence_trigger', ['neutral'], {}, { trackActivity: false });
      }

      emotionSequenceActiveRef.current = false;
      previousModeRef.current = emotionMode;
      return;
    }

    if (
      previousMode
      && previousMode !== emotionMode
      && sequenceActiveRef.current
      && emotionSequenceActiveRef.current
    ) {
      emotionSequenceActiveRef.current = false;
      node.emit('sequence_trigger', ['neutral'], {}, { trackActivity: false });
    }

    scheduleModeAction(INITIAL_TRIGGER_MIN_MS, INITIAL_TRIGGER_MAX_MS);
    previousModeRef.current = emotionMode;
  }, [emotionMode]);

  return null;
};

export default EmotionModeControl;
