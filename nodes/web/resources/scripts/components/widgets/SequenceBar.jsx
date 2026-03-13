/**
 * SequenceBar Component
 * Renders compact scene buttons for the showtime page.
 */
import React from 'react';
import node from '../../Node';

const SEQUENCES = [
  { id: 'neutral', label: 'Ruhig', title: 'Zur Ruhepose', duration: 0.6 },
  { id: 'wave-hello', label: 'Winken', duration: 3.4 },
  { id: 'peekaboo', label: 'Kuckuck', duration: 4.4 },
  { id: 'curious-scan', label: 'Neugierig', duration: 9.8 },
  { id: 'hands-up', label: 'Arme hoch', duration: 3.7 },
  { id: 'pirouette', label: 'Pirouette', duration: 5.5 },
  { id: 'candy', label: 'Bonbon?', duration: 5.6 },
  { id: 'party', label: 'Party', duration: 8.6 },
  { id: 'spin-wiggle', label: 'Drehwackel', duration: 2.2 },
  { id: 'double-take', label: 'Hoppla', duration: 1.6 },
  { id: 'shimmy', label: 'Wackeltanz', duration: 1.9 },
  { id: 'suche', label: 'Suche', duration: 2.2 },
];

const LEFT_SEQUENCES = SEQUENCES.slice(0, Math.ceil(SEQUENCES.length / 2));
const RIGHT_SEQUENCES = SEQUENCES.slice(Math.ceil(SEQUENCES.length / 2));

const formatDuration = (seconds) => `${seconds.toFixed(1)}s`;

const Button = ({ id, label, title, duration }) => (
  <button
    className="sequence-bar__btn"
    onClick={() => node.emit('sequence_trigger', [id])}
    title={title || label}
  >
    <span className="sequence-bar__btn-content">
      <span className="sequence-bar__label">{label}</span>
      {duration ? <span className="sequence-bar__duration">{formatDuration(duration)}</span> : null}
    </span>
  </button>
);

const SequenceBar = () => {
  const styles = `
    .sequence-bar {
      display: grid;
      grid-template-columns: clamp(72px, 19vw, 94px) minmax(0, 1fr) clamp(72px, 19vw, 94px);
      gap: 8px;
      width: 100%;
      height: 100%;
      align-items: start;
    }

    .sequence-bar__rail {
      display: grid;
      gap: 4px;
      align-content: start;
    }

    .sequence-bar__center {
      min-height: 100%;
      pointer-events: none;
    }

    @media (orientation: landscape) and (min-width: 560px) {
      .sequence-bar {
        grid-template-columns: clamp(84px, 13vw, 112px) minmax(0, 1fr) clamp(84px, 13vw, 112px);
      }
    }

    .sequence-bar__btn {
      padding: 9px 6px;
      min-height: 46px;
      font-size: 0.82rem;
      line-height: 1.1;
      font-weight: 600;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.10);
      background: rgba(255,255,255,0.04);
      color: #fff;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.88), 0 0 10px rgba(0, 0, 0, 0.35);
      cursor: pointer;
      transition: all .2s;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }
    .sequence-bar__btn-content {
      display: inline-flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }
    .sequence-bar__duration {
      font-size: 0.66rem;
      font-weight: 500;
      opacity: 0.82;
      white-space: nowrap;
    }
    .sequence-bar__btn:hover {
      background: rgba(255,255,255,0.08);
      border-color: var(--primary);
      transform: translateY(-1px);
    }
    .sequence-bar__btn:active {
      transform: translateY(0);
    }
  `;

  return (
    <div className="sequence-bar">
      <style>{styles}</style>
      <div className="sequence-bar__rail sequence-bar__rail--left">
        {LEFT_SEQUENCES.map((sequence) => (
          <Button key={sequence.id} {...sequence} />
        ))}
      </div>
      <div className="sequence-bar__center" aria-hidden="true" />
      <div className="sequence-bar__rail sequence-bar__rail--right">
        {RIGHT_SEQUENCES.map((sequence) => (
          <Button key={sequence.id} {...sequence} />
        ))}
      </div>
    </div>
  );
};

export default SequenceBar;
