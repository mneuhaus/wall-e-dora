/**
 * ShowtimeView Component
 *
 * Full-page scene/action launcher.
 *
 * @component
 */
import React from 'react';
import SequenceBar from '../components/widgets/SequenceBar';

const ShowtimeView = () => {
  const styles = `
    .showtime-view {
      height: 100%;
      min-height: 100%;
      overflow: hidden;
      padding: 8px;
      box-sizing: border-box;
    }

    .showtime-view .sequence-bar {
      margin-top: 0;
      min-height: calc(100vh - 62px);
      gap: 8px;
    }

    .showtime-view .sequence-bar__btn {
      min-height: 50px;
      padding: 9px 5px;
      font-size: 0.78rem;
      border-radius: 14px;
    }

    .showtime-view .sequence-bar__rail {
      gap: 8px;
    }

    @media (max-width: 359px) {
      .showtime-view .sequence-bar {
        grid-template-columns: 68px minmax(0, 1fr) 68px;
      }

      .showtime-view .sequence-bar__btn {
        min-height: 48px;
        font-size: 0.75rem;
      }
    }

    @media (orientation: landscape) and (min-width: 560px) {
      .showtime-view .sequence-bar {
        min-height: calc(100vh - 58px);
      }

      .showtime-view .sequence-bar__btn {
        min-height: 46px;
        font-size: 0.74rem;
      }
    }

    @media (min-width: 760px) {
      .showtime-view .sequence-bar__btn {
        min-height: 48px;
        font-size: 0.76rem;
      }
    }
  `;

  return (
    <div className="showtime-view">
      <style>{styles}</style>
      <SequenceBar />
    </div>
  );
};

export default ShowtimeView;
