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
      overflow: auto;
      padding: 10px;
      box-sizing: border-box;
    }

    .showtime-view .sequence-bar {
      margin-top: 0;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .showtime-view .sequence-bar__btn {
      min-height: 76px;
      font-size: 1rem;
      border-radius: 18px;
    }

    @media (min-width: 760px) {
      .showtime-view .sequence-bar {
        grid-template-columns: repeat(3, minmax(0, 1fr));
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
