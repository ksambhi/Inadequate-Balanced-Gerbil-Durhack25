import React, { useState, useEffect, useRef } from 'react';
import type { Attendee, RawAttendee } from '../../types/data.types'; 
import styles from './AttendeeManager.module.scss';
import { MOCK_ATTENDEES } from '../../hooks/useSeatingAlgorithm'; 

interface Props {
  onSetAttendees: (attendees: Attendee[]) => void;
  onGeneratePlan: (finalAttendees: Attendee[]) => void;
}

export const AttendeeManager: React.FC<Props> = ({ onSetAttendees, onGeneratePlan }) => {
  const [rawAttendees, setRawAttendees] = useState<RawAttendee[]>([
    { id: '1', name: '', phoneNumber: '' }
  ]);
  const [attendeesWithViews, setAttendeesWithViews] = useState<Attendee[]>([]);
  const [invitesSent, setInvitesSent] = useState(false);
  const [rsvpStatus, setRsvpStatus] = useState<Record<string, boolean>>({});
  
  const pollingIntervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);

  // --- HANDLERS FOR DYNAMIC INPUTS ---

  const handleInputChange = (index: number, field: keyof RawAttendee, value: string) => {
    const newAttendees = [...rawAttendees];
    (newAttendees[index] as any)[field] = value; 
    setRawAttendees(newAttendees);
  };

  const handleAddRow = () => {
    const newId = (Date.now() + Math.random()).toString();
    setRawAttendees([...rawAttendees, { id: newId, name: '', phoneNumber: '' }]);
  };

  const handleRemoveRow = (index: number) => {
    const newAttendees = rawAttendees.filter((_, i) => i !== index);
    setRawAttendees(newAttendees);
  };

  // Poll the backend to check RSVP status
  const pollRsvpStatus = async (attendeeIds: string[]) => {
    try {
      // Replace with your actual API endpoint
      const response = await fetch('/api/rsvp-status', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ attendeeIds }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch RSVP status');
      }

      const data = await response.json();
      // Expecting response like: { rsvpStatus: { "id1": true, "id2": false, ... } }
      setRsvpStatus(data.rsvpStatus);

      // Check if all have RSVP'd
      const allRsvped = attendeeIds.every(id => data.rsvpStatus[id]);
      if (allRsvped) {
        stopPolling();
      }
    } catch (error) {
      console.error('Error polling RSVP status:', error);
    }
  };

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  const markAllAsRsvped = (attendeeIds: string[]) => {
    const allRsvped: Record<string, boolean> = {};
    attendeeIds.forEach(id => {
      allRsvped[id] = true;
    });
    setRsvpStatus(allRsvped);
    stopPolling();
  };

  // Start polling when invites are sent
  const startPolling = (attendeeIds: string[]) => {
    // Poll every 2 seconds
    pollingIntervalRef.current = window.setInterval(() => {
      pollRsvpStatus(attendeeIds);
    }, 2000);

    // Timeout after 30 seconds - mark everyone as RSVP'd
    timeoutRef.current = window.setTimeout(() => {
      console.log('30 second timeout reached, marking all as RSVP\'d');
      markAllAsRsvped(attendeeIds);
    }, 10000);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, []);

  // --- MOCK INVITATION LOGIC ---

  const handleSendInvites = async () => {
    console.log('Sending invites to:', rawAttendees);
    const validAttendees = rawAttendees.filter(a => a.name.trim() !== '');

    if (validAttendees.length === 0) return;

    // Initialize RSVP status for all invited attendees
    const initialRsvpStatus: Record<string, boolean> = {};
    validAttendees.forEach(attendee => {
      initialRsvpStatus[attendee.id] = false;
    });
    setRsvpStatus(initialRsvpStatus);

    // Map to mock data
    const finalData: Attendee[] = validAttendees.map((raw, index) => ({
      id: raw.id,
      name: raw.name,
      phone: raw.phoneNumber,
      email: `attendee${index + 1}@example.com`,
      opinions: MOCK_ATTENDEES[index % MOCK_ATTENDEES.length].opinions
    }));

    console.log("Right before sending to backend");

    setAttendeesWithViews(finalData);
    setInvitesSent(true);

    // Call the parent's onSetAttendees to handle the PUT request
    await onSetAttendees(finalData);

    // Start polling for RSVP status
    const attendeeIds = validAttendees.map(a => a.id);
    startPolling(attendeeIds);
  };

  const totalInvited = rawAttendees.filter(a => a.name.trim() !== '').length;
  const totalRsvped = Object.values(rsvpStatus).filter(status => status).length;
  const allRsvped = invitesSent && totalRsvped === totalInvited && totalInvited > 0;

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
              disabled={invitesSent}
            />
            <input
              type="text"
              placeholder="Phone (e.g., 555-1234)"
              value={attendee.phoneNumber}
              onChange={(e) => handleInputChange(index, 'phoneNumber', e.target.value)}
              disabled={invitesSent}
            />
            <button 
                onClick={() => handleRemoveRow(index)} 
                disabled={rawAttendees.length === 1 || invitesSent}
                className={styles.removeButton}
            >
                ➖
            </button>
          </div>
        ))}

        {!invitesSent && (
          <button onClick={handleAddRow} className={styles.addButton}>
            ➕ Add Another Attendee
          </button>
        )}
      </div>

      {!invitesSent ? (
        <button 
          onClick={handleSendInvites} 
          className={styles.inviteButton} 
          disabled={totalInvited === 0}
        >
          Send Invites to {totalInvited} {totalInvited === 1 ? 'Person' : 'People'}
        </button>
      ) : (
        <div className={styles.rsvpStatusSection}>
          <p className={styles.rsvpText}>
            📨 Invites sent! Waiting for RSVPs...
          </p>
          <div className={styles.rsvpProgress}>
            <div className={styles.rsvpBar}>
              <div 
                className={styles.rsvpFill} 
                style={{ width: `${(totalRsvped / totalInvited) * 100}%` }}
              />
            </div>
            <span className={styles.rsvpCount}>
              {totalRsvped} / {totalInvited} responded
            </span>
          </div>
        </div>
      )}

      {attendeesWithViews.length > 0 && (
        <div className={`${styles.dataLoadedSection} ${allRsvped ? styles.highlighted : ''}`}>
          {allRsvped ? (
            <>
              <p className={styles.allRsvpedText}>
                ✅ All attendees have RSVP'd! Ready to generate seating plan.
              </p>
              <button 
                onClick={() => onGeneratePlan(attendeesWithViews)} 
                className={styles.generateButton}
              >
                Generate Seating Plan
              </button>
            </>
          ) : (
            <p className={styles.waitingText}>
              ⏳ Waiting for all RSVPs before generating seating plan...
            </p>
          )}
        </div>
      )}
    </div>
  );
};