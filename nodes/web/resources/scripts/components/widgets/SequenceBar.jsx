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
    .sequence-bar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; }
    .sequence-bar__btn { padding: 10px 8px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.06); color: #fff; cursor: pointer; transition: all .2s; }
    .sequence-bar__btn:hover { background: rgba(255,255,255,0.12); border-color: var(--primary); }
  `;
  return (
    <div className="sequence-bar">
      <style>{styles}</style>
      <Button id="hands-up" label="Hands Up" />
      <Button id="candy" label="Candy ?" />
      <Button id="party" label="Party" />
    </div>
  );
};

export default SequenceBar;

