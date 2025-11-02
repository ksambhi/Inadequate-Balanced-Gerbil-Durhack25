import type { Attendee } from '../types/data.types';


// --- MOCK ATTENDEES DATA ---
// This array simulates the data returned after attendees RSVP and send their views.
// src/hooks/useSeatingAlgorithm.ts

export const MOCK_ATTENDEES: Attendee[] = [
    { 
        id: 'a1', 
        name: 'Alice C.', 
        views: { views: [1, 0.2] }
    },
    { 
        id: 'a2', 
        name: 'Bob L.', 
        views: { views: [0, 0.8] }
    },
    // ... continue for all mock attendees
];
// ----------------------------

/**
 * MOCK Hook Function (Not actually used in App.tsx currently, but included
 * to satisfy the name expectation and provide a place for future logic.)
 *
 * @param attendees The list of attendees with their views.
 * @param settings The event parameters (table size, chaos factor).
 * @returns A mock seating plan (or would call the backend for a real one).
 */
export const useSeatingAlgorithm = (attendees: Attendee[], settings: any) => {
    // In a real application, this is where you'd execute the complex seating logic
    // or call the backend API:
    // const realPlan = await fetch('/api/seating-plan', { ... });

    return {
        // We just return the mock attendees here for completeness
        generatedPlan: attendees 
    };
};