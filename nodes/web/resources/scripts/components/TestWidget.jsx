import React, { useState } from 'react';

const TestWidget = () => {
  const [counter, setCounter] = useState(0);
  
  const incrementCounter = () => {
    setCounter(counter + 1);
  };
  
  return (
    <div className="test-widget">
      <div className="card medium">
        <div className="card-content">
          <span className="card-title">Test Widget</span>
          <p>This is a test widget to demonstrate React components</p>
          <p>Counter: {counter}</p>
          <button onClick={incrementCounter} className="btn">
            Increment
          </button>
        </div>
      </div>
    </div>
  );
};

export default TestWidget;