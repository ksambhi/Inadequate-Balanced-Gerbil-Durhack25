import React, { useState } from 'react';
import type { EventSettings } from '../../types/data.types';
import styles from './EventCreationForm.module.scss';

interface Props {
  onSubmit: (settings: EventSettings) => void;
}

export const EventCreationForm: React.FC<Props> = ({ onSubmit }) => {
  const [eventName, setEventName] = useState('My Awesome Event');
  const [numberOfTables, setNumberOfTables] = useState(10);
  const [tableSize, setTableSize] = useState(8);
  const [chaosFactor, setChaosFactor] = useState(5);
  const [views, setViews] = useState(['chocolate', 'age']);
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      eventName,
      numberOfTables,
      tableSize,
      chaosFactor,
      views
    });
  };

  return (
    <form onSubmit={handleSubmit} className={styles.formContainer}>
      <h2>Create Your Event</h2>
      
      <div className={styles.formField}>
        <label htmlFor="eventName">Event Name</label>
        <input
          id="eventName"
          type="text"
          value={eventName}
          onChange={(e) => setEventName(e.target.value)}
        />
      </div>

      <div className={styles.formField}>
        <label htmlFor="numTables">Number of Tables</label>
        <input
          id="numTables"
          type="number"
          value={numberOfTables}
          onChange={(e) => setNumberOfTables(parseInt(e.target.value))}
        />
      </div>
      
      <div className={styles.formField}>
        <label htmlFor="tableSize">Seats per Table</label>
        <input
          id="tableSize"
          type="number"
          value={tableSize}
          onChange={(e) => setTableSize(parseInt(e.target.value))}
        />
      </div>

      <div className={styles.formField}>
        <label htmlFor="chaos">Chaos Factor: {chaosFactor}</label>
        <span>Optimized</span>
        <input
          id="chaos"
          type="range"
          min="1"
          max="10"
          value={chaosFactor}
          onChange={(e) => setChaosFactor(parseInt(e.target.value))}
          className={styles.slider}
        />
        <span>Chaotic</span>
      </div>

      <button type="submit" className={styles.submitButton}>
        Load Attendees & Continue
      </button>
    </form>
  );
};