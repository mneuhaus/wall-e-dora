import React from 'react';
import { useAppContext } from '../../../contexts/AppContext';

const ServoSelector = ({ value, onChange, label = "Servo" }) => {
  const { availableServos } = useAppContext();
  
  const handleChange = (e) => {
    const selectedValue = e.target.value === "null" ? null : e.target.value;
    onChange(selectedValue);
  };

  return (
    <div className="field">
      <label className="label" htmlFor="servo-selector">{label}</label>
      <select 
        id="servo-selector"
        value={value === null ? "null" : value} 
        onChange={handleChange}
        className="select"
      >
        <option value="null">None</option>
        {availableServos && availableServos.map(servo => (
          <option key={servo.id} value={servo.id}>
            {servo.name || `Servo ${servo.id}`}
          </option>
        ))}
      </select>
    </div>
  );
};

export default ServoSelector;