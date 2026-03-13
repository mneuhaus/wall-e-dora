/**
 * SequenceBar Component
 * Renders compact scene buttons for the showtime page.
 */
import React from 'react';
import node from '../../Node';

const SEQUENCES = [
  { id: 'neutral', label: 'Ruhig', title: 'Zur Ruhepose' },
  { id: 'wave-hello', label: 'Winken' },
  { id: 'peekaboo', label: 'Kuckuck' },
  { id: 'curious-scan', label: 'Neugierig' },
  { id: 'hands-up', label: 'Arme hoch' },
  { id: 'candy', label: 'Bonbon?' },
  { id: 'party', label: 'Party' },
  { id: 'spin-wiggle', label: 'Drehwackel' },
  { id: 'double-take', label: 'Hoppla' },
  { id: 'shimmy', label: 'Wackeltanz' },
];

const Button = ({ id, label, title }) => (
  <button
    className="sequence-bar__btn"
    onClick={() => node.emit('sequence_trigger', [id])}
    title={title || label}
  >
    {label}
  </button>
);

const SequenceBar = () => {
  const styles = `
    .sequence-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-top: 12px;
      width: 100%;
    }
    @media (max-width: 900px) {
      .sequence-bar { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 600px) {
      .sequence-bar { grid-template-columns: repeat(2, 1fr); }
    }

    .sequence-bar__btn {
      padding: 12px 10px;
      min-height: 52px;
      font-size: 0.92rem;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.06);
      color: #fff;
      cursor: pointer;
      transition: all .2s;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }
    .sequence-bar__btn:hover {
      background: rgba(255,255,255,0.12);
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
      {SEQUENCES.map((sequence) => (
        <Button key={sequence.id} {...sequence} />
      ))}
    </div>
  );
};

export default SequenceBar;
