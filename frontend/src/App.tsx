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
    axios
      .post(`${BASE_URL}/events/create`, {
        name: eventSettings.eventName,
        total_tables: eventSettings.numberOfTables,
        ppl_per_table: eventSettings.tableSize,
        chaos_temp: eventSettings.chaosFactor,
      })
      .then((response) => {
        console.log("Event created successfully:", response.data);
        setEventId(response.data.id.toString());
        setSettings(eventSettings);
        setStep("MANAGE_ATTENDEES");
      })
      .catch((error) => {
        console.error("Error creating event:", error);
      });
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
  const handleGeneratePlan = (finalAttendees: Attendee[]) => {

    // --- MOCK SEATING PLAN GENERATION ---
    // Use the stored settings for more realistic mock tables
    const tableCapacity = settings.tableSize;
    const mockTables = [];
    let attendeeIndex = 0;

    for (let i = 0; i < settings.numberOfTables; i++) {
      const attendeesForTable = finalAttendees.slice(
        attendeeIndex,
        attendeeIndex + tableCapacity
      );
      mockTables.push({
        id: i + 1,
        capacity: tableCapacity,
        attendees: attendeesForTable,
      });
      attendeeIndex += tableCapacity;
    }

    const mockPlan: SeatingPlan = {
      tables: mockTables.filter((t) => t.attendees.length > 0), // Remove empty tables
    };
    // ------------------------------------

    setSeatingPlan(mockPlan);
    setStep("VIEW_PLAN");
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
