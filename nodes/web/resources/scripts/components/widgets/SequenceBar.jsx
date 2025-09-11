/**
 * SequenceBar Component
 * Renders three quick-action sequence buttons beneath the eyes.
 */
import React from 'react';
import node from '../../Node';

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
      grid-template-columns: repeat(4, 1fr); /* two rows on desktop */
      gap: 10px; 
      margin-top: 12px; 
      width: 100%;
    }
    /* On tablets/phones: larger tap targets by reducing columns */
    @media (max-width: 900px) {
      .sequence-bar { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 600px) {
      .sequence-bar { grid-template-columns: repeat(2, 1fr); }
    }

    .sequence-bar__btn { 
      padding: 14px 12px; 
      min-height: 56px; 
      font-size: 0.95rem;
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
      <Button id="hands-up" label="Hands Up" />
      <Button id="candy" label="Candy ?" />
      <Button id="party" label="Party" />
      <Button id="neutral" label="Neutral" title="Return to neutral (close door)" />
      <Button id="wave-hello" label="Wave" />
      <Button id="curious-scan" label="Curious" />
      <Button id="peekaboo" label="Peekaboo" />
    </div>
  );
};

export default SequenceBar;
