export const EMOTION_MODES = [
  {
    id: 'neutral',
    label: 'Ruhig',
    icon: 'fas fa-pause',
    accent: 'rgba(255, 255, 255, 0.18)',
    sequences: [],
  },
  {
    id: 'joy',
    label: 'Freude',
    icon: 'fas fa-heart',
    accent: 'rgba(255, 191, 0, 0.42)',
    sequences: ['hands-up', 'wave-hello', 'spin-wiggle', 'candy'],
    minDelayMs: 3200,
    maxDelayMs: 7000,
  },
  {
    id: 'sadness',
    label: 'Trauer',
    icon: 'fas fa-cloud',
    accent: 'rgba(96, 165, 250, 0.34)',
    sequences: ['idle-listen', 'idle-peek', 'curious-scan'],
    minDelayMs: 4200,
    maxDelayMs: 9000,
  },
  {
    id: 'fear',
    label: 'Angst',
    icon: 'fas fa-bolt',
    accent: 'rgba(248, 113, 113, 0.36)',
    sequences: ['double-take', 'peekaboo', 'suche'],
    minDelayMs: 2600,
    maxDelayMs: 5600,
  },
  {
    id: 'laugh',
    label: 'Lachen',
    icon: 'fas fa-smile',
    accent: 'rgba(74, 222, 128, 0.36)',
    sequences: ['shimmy', 'spin-wiggle', 'double-take', 'wave-hello'],
    minDelayMs: 2800,
    maxDelayMs: 5800,
  },
  {
    id: 'dance',
    label: 'Tanzen',
    icon: 'fas fa-music',
    accent: 'rgba(244, 114, 182, 0.34)',
    sequences: ['shimmy', 'spin-wiggle', 'pirouette', 'party'],
    minDelayMs: 2200,
    maxDelayMs: 4800,
  },
  {
    id: 'wave',
    label: 'Winken',
    icon: 'fas fa-hand-paper',
    accent: 'rgba(192, 132, 252, 0.34)',
    sequences: ['wave-hello', 'hands-up', 'double-take'],
    minDelayMs: 3400,
    maxDelayMs: 7000,
  },
];

export const EMOTION_MODE_BY_ID = Object.fromEntries(
  EMOTION_MODES.map((mode) => [mode.id, mode]),
);

export function getEmotionMode(modeId) {
  return EMOTION_MODE_BY_ID[modeId] || EMOTION_MODE_BY_ID.neutral;
}

export function pickNextEmotionSequence(modeId, lastSequenceId = null) {
  const mode = getEmotionMode(modeId);
  const candidates = Array.isArray(mode.sequences) ? mode.sequences : [];

  if (candidates.length === 0) {
    return null;
  }

  const filtered = candidates.length > 1
    ? candidates.filter((sequenceId) => sequenceId !== lastSequenceId)
    : candidates;

  const pool = filtered.length > 0 ? filtered : candidates;
  return pool[Math.floor(Math.random() * pool.length)];
}
