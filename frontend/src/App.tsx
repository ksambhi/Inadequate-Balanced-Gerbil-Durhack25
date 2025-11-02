import React, { useState } from "react";
// import './styles/global.scss'; // Ensure global styles are imported
import "./App.scss";
import { EventCreationForm } from "./components/EventCreationForm/EventCreationForm";
import { AttendeeManager } from "./components/AttendeeManager/AttendeeManager";
import { SeatingVisualizer } from "./components/SeatingVisualizer/SeatingVisualizer";
import type { EventSettings, Attendee, SeatingPlan } from "./types/data.types";

// --- MOCK DATA ---
import { MOCK_ATTENDEES } from "./hooks/useSeatingAlgorithm";
import axios from "axios";
import { BASE_URL } from "./utils/constants";
// -----------------

// Define a safe initial state for EventSettings
const INITIAL_SETTINGS: EventSettings = {
  eventName: "New Event",
  numberOfTables: 2,
  tableSize: 8,
  chaosFactor: 0.5,
  // IMPORTANT: Initialize 'views' array to prevent TypeError in SeatingVisualizer
  views: ["politics", "age"],
};

type AppStep = "CREATE_EVENT" | "MANAGE_ATTENDEES" | "VIEW_PLAN";

function App() {
  const [step, setStep] = useState<AppStep>("CREATE_EVENT");
  // 1. INITIALIZE settings with a concrete object, not 'null'
  const [settings, setSettings] = useState<EventSettings>(INITIAL_SETTINGS);

  // Attendee state is no longer fully needed here as AttendeeManager now handles mock loading
  const [seatingPlan, setSeatingPlan] = useState<SeatingPlan | null>(null);

  // event id
  const [eventId, setEventId] = useState<string | null>(null);

  // 1. Called by EventCreationForm
  const handleEventCreate = (eventSettings: EventSettings) => {
    // Axios POST BASE_URL/events/create
    /// @ts-expect-error: cba
    setEventId(eventSettings.eventId);
    setSettings(eventSettings);
    setStep("MANAGE_ATTENDEES");
  };

  // 2. Called by AttendeeManager when invites are sent
  const handleSetAttendees = (finalAttendees: Attendee[]) => {
    // PUT /{event_id}/attendees/
    if (!eventId) {
      console.error("Event ID is null. Cannot add attendees.");
      return;
    }

    axios
      .put(`${BASE_URL}/events/${eventId}/attendees`, {
        attendees: finalAttendees.map((a) => ({
          name: a.name,
          phone: a.phone,
          email: a.email,
        })),
      })
      .then((response) => {
        console.log("Attendees added successfully:", response.data);
      })
      .catch((error) => {
        console.error("Error adding attendees:", error);
      });
  };

  // 3. Called by AttendeeManager when ready to generate seating plan
  const handleGeneratePlan = async () => {
    if (!eventId) {
      console.error("No event ID available");
      return;
    }

    try {
      // Make request to backend to allocate seats
      const response = await axios.post(
        `${BASE_URL}/events/${eventId}/allocate_seats`,
        null, // No body needed
        {
          params: { verbose: false }
        }
      );

      console.log("Seating allocation successful:", response.data);
      
      // The seating plan will be fetched automatically by SeatingVisualizer
      // Just set a placeholder plan to trigger the VIEW_PLAN step
      const placeholderPlan: SeatingPlan = {
        tables: []
      };
      
      setSeatingPlan(placeholderPlan);
      setStep("VIEW_PLAN");
    } catch (error) {
      console.error("Error allocating seats:", error);
      // You might want to show an error message to the user here
    }
  };

  // Render the correct component based on the current step
  return (
    <div className="app-container">
      {step === "CREATE_EVENT" && (
        <EventCreationForm onSubmit={handleEventCreate} />
      )}

      {step === "MANAGE_ATTENDEES" && (
        <AttendeeManager 
          onSetAttendees={handleSetAttendees}
          onGeneratePlan={handleGeneratePlan}
          eventId={eventId}
        />
      )}
      {/* 2. Pass 'settings' to SeatingVisualizer, which now requires it */}
      {step === "VIEW_PLAN" && seatingPlan && settings && (
        <SeatingVisualizer
          plan={seatingPlan}
          settings={settings} // Now correctly passing the initialized settings
        />
      )}
    </div>
  );
}

export default App;
