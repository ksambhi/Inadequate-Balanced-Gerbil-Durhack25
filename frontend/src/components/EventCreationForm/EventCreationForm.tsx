import React, { useState } from 'react';
import type { EventSettings } from '../../types/data.types';
import { BASE_URL } from '../../utils/constants';
import styles from './EventCreationForm.module.scss';

interface Props {
  onSubmit: (settings: EventSettings) => void;
}

export const EventCreationForm: React.FC<Props> = ({ onSubmit }) => {
  const [eventName, setEventName] = useState('My Awesome Event');
  const [numberOfTables, setNumberOfTables] = useState(10);
  const [tableSize, setTableSize] = useState(8);
  const [chaosFactor, setChaosFactor] = useState(5);
  const [views, setViews] = useState<string[]>(['chocolate', 'age']);
  const [newView, setNewView] = useState('');

  const handleAddView = () => {
    if (newView.trim() && !views.includes(newView.trim())) {
      setViews([...views, newView.trim()]);
      setNewView('');
    }
  };

  const handleRemoveView = (index: number) => {
    setViews(views.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Save event to backend
    try {
      const response = await fetch(`${BASE_URL}/events/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: eventName,
          total_tables: numberOfTables,
          ppl_per_table: tableSize,
          chaos_temp: chaosFactor,
          opinions: views
        })
      });
      if (!response.ok) throw new Error('Failed to create event');
      const eventData = await response.json();
      // Pass event data to parent
      onSubmit({
        eventName,
        numberOfTables,
        tableSize,
        chaosFactor,
        views,
        eventId: eventData.id // If you want to pass the event id
      });
    } catch (err) {
      alert('Error creating event');
    }
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
          <div className={styles.sliderContainer}>
            <span className={styles.sliderLabel}>Optimized</span>
            <input
              id="chaos"
              type="range"
              min="1"
              max="10"
              value={chaosFactor}
              onChange={(e) => setChaosFactor(parseInt(e.target.value))}
              className={styles.slider}
            />
            <span className={styles.sliderLabel}>Chaotic</span>
          </div>
        </div>

      <div className={styles.formField}>
        <label htmlFor="views">Opinion Questions (Topics)</label>
        <div className={styles.viewsList}>
          {views.map((view, idx) => (
            <div key={view} className={styles.viewItem}>
              {view}
              <button type="button" onClick={() => handleRemoveView(idx)} className={styles.removeViewBtn}>✕</button>
            </div>
          ))}
        </div>
        <div className={styles.addViewContainer}>
          <input
            type="text"
            placeholder="Add a topic/question"
            value={newView}
            onChange={(e) => setNewView(e.target.value)}
          />
          <button type="button" onClick={handleAddView} className={styles.addViewBtn}>Add</button>
        </div>
      </div>

      <button type="submit" className={styles.submitButton}>
        Load Attendees & Continue
      </button>
    </form>
  );
};