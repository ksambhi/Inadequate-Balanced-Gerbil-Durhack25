import React, { useState } from 'react';
import type { Attendee, RawAttendee } from '../../types/data.types'; 
import styles from './AttendeeManager.module.scss';
import { MOCK_ATTENDEES } from '../../hooks/useSeatingAlgorithm'; 

interface Props {
  onSetAttendees: (attendees: Attendee[]) => void;
  onGeneratePlan: (finalAttendees: Attendee[]) => void;
}

export const AttendeeManager: React.FC<Props> = ({ onSetAttendees, onGeneratePlan }) => {
  // New state to manage an array of raw attendee objects (Name & Phone)
  const [rawAttendees, setRawAttendees] = useState<RawAttendee[]>([
    { id: '1', name: '', phoneNumber: '' } // Start with one empty row
  ]);
  const [attendeesWithViews, setAttendeesWithViews] = useState<Attendee[]>([]);

  // --- HANDLERS FOR DYNAMIC INPUTS ---

  const handleInputChange = (index: number, field: keyof RawAttendee, value: string) => {
    const newAttendees = [...rawAttendees];
    // TypeScript trick to update the correct field
    (newAttendees[index] as any)[field] = value; 
    setRawAttendees(newAttendees);
  };

  const handleAddRow = () => {
    // Adds a new empty row with a unique ID
    const newId = (Date.now() + Math.random()).toString();
    setRawAttendees([...rawAttendees, { id: newId, name: '', phoneNumber: '' }]);
  };

  const handleRemoveRow = (index: number) => {
    const newAttendees = rawAttendees.filter((_, i) => i !== index);
    setRawAttendees(newAttendees);
  };

  // --- MOCK INVITATION LOGIC (Simplified) ---

  const handleSendInvites = () => {
    const validAttendees = rawAttendees.filter(a => a.name.trim() !== '');

    if (validAttendees.length === 0) return;

    // SIMULATE DATA GATHERING (MOCK): 
    // We map our valid input list to the prepared MOCK_ATTENDEES data
    const finalData: Attendee[] = validAttendees.map((raw, index) => ({
      id: raw.id,
      name: raw.name,
      phone: raw.phoneNumber,
      email: `attendee${index + 1}@example.com`,
      // Assign mock view data to the corresponding input attendee
      opinions: MOCK_ATTENDEES[index % MOCK_ATTENDEES.length].opinions
    }));

    setAttendeesWithViews(finalData);
    // Call the parent's onSetAttendees to handle the PUT request
    onSetAttendees(finalData);
  };

  const totalInvited = rawAttendees.filter(a => a.name.trim() !== '').length;

  return (
    <div className={styles.managerContainer}>
      <h2>Define Invitees</h2>
      
      <div className={styles.attendeeList}>
        <div className={styles.headerRow}>
            <strong>Name</strong>
            <strong>Phone Number</strong>
            <span className={styles.actionsHeader}>Actions</span>
        </div>

        {rawAttendees.map((attendee, index) => (
          <div key={attendee.id} className={styles.inputRow}>
            <input
              type="text"
              placeholder="Attendee Name"
              value={attendee.name}
              onChange={(e) => handleInputChange(index, 'name', e.target.value)}
            />
            <input
              type="text"
              placeholder="Phone (e.g., 555-1234)"
              value={attendee.phoneNumber}
              onChange={(e) => handleInputChange(index, 'phoneNumber', e.target.value)}
            />
            <button 
                onClick={() => handleRemoveRow(index)} 
                disabled={rawAttendees.length === 1}
                className={styles.removeButton}
            >
                ➖
            </button>
          </div>
        ))}

        <button onClick={handleAddRow} className={styles.addButton}>
          ➕ Add Another Attendee
        </button>
      </div>

      <button onClick={handleSendInvites} className={styles.inviteButton} disabled={totalInvited === 0}>
        Send Invites (MOCK: Load Data for {totalInvited} People)
      </button>

      {attendeesWithViews.length > 0 && (
        <div className={styles.dataLoadedSection}>
          <p>
            ✅ View data gathered for <strong>{attendeesWithViews.length}</strong> attendees.
          </p>
          <button 
            onClick={() => onGeneratePlan(attendeesWithViews)} 
            className={styles.generateButton}
          >
            Generate Seating Plan
          </button>
        </div>
      )}
    </div>
  );
};