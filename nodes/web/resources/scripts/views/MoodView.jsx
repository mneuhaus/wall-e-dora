/**
 * MoodView Component
 *
 * Dedicated page for persistent emotion-style behavior presets.
 *
 * @component
 */
import React from 'react';
import { useAppContext } from '../contexts/AppContext';
import { EMOTION_MODES } from '../emotionModes';

const MoodView = () => {
  const { emotionMode, setEmotionMode } = useAppContext();

  const styles = `
    .mood-view {
      height: 100%;
      min-height: 100%;
      overflow: hidden;
      padding: 8px;
      box-sizing: border-box;
    }

    .mood-status {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.16);
      background: rgba(255, 255, 255, 0.08);
      color: rgba(255, 255, 255, 0.92);
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.88);
    }

    .mood-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      min-height: calc(100vh - 74px);
      align-content: start;
    }

    .mood-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 88px;
      padding: 12px 10px;
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.14);
      background: rgba(255, 255, 255, 0.06);
      color: #fff;
      cursor: pointer;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.92), 0 0 12px rgba(0, 0, 0, 0.35);
      box-shadow: 0 10px 22px rgba(0, 0, 0, 0.12);
      backdrop-filter: blur(6px);
      transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }

    .mood-card:hover {
      transform: translateY(-1px);
      border-color: rgba(255, 191, 0, 0.34);
    }

    .mood-card:active {
      transform: translateY(0);
    }

    .mood-card--active {
      border-color: rgba(255, 191, 0, 0.52);
      background: var(--mood-accent, rgba(255, 191, 0, 0.18));
      box-shadow: 0 0 0 1px rgba(255, 191, 0, 0.18), 0 14px 28px rgba(0, 0, 0, 0.18);
    }

    .mood-card--neutral {
      grid-column: 1 / -1;
      min-height: 70px;
      flex-direction: row;
      justify-content: center;
    }

    .mood-card__icon {
      font-size: 1.3rem;
      opacity: 0.95;
    }

    .mood-card__label {
      font-size: 0.88rem;
      font-weight: 700;
      line-height: 1.05;
      text-align: center;
    }

    @media (orientation: landscape) and (min-width: 560px) {
      .mood-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }

      .mood-card--neutral {
        grid-column: span 2;
      }
    }
  `;

  const activeMode = EMOTION_MODES.find((mode) => mode.id === emotionMode) || EMOTION_MODES[0];

  return (
    <div className="mood-view">
      <style>{styles}</style>
      <div className="mood-status">
        <i className={activeMode.icon} aria-hidden="true"></i>
        <span>Aktiv: {activeMode.label}</span>
      </div>

      <div className="mood-grid">
        {EMOTION_MODES.map((mode) => {
          const isActive = mode.id === emotionMode;

          return (
            <button
              key={mode.id}
              type="button"
              aria-pressed={isActive}
              className={`mood-card ${isActive ? 'mood-card--active' : ''} ${mode.id === 'neutral' ? 'mood-card--neutral' : ''}`}
              style={{ '--mood-accent': mode.accent }}
              onClick={() => setEmotionMode(mode.id)}
            >
              <i className={`mood-card__icon ${mode.icon}`} aria-hidden="true"></i>
              <span className="mood-card__label">{mode.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default MoodView;
