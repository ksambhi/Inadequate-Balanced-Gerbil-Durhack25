export type AttendeeViews = {
  views: number[];
};

// The initial data structure the organizer provides
export interface RawAttendee {
  id: string; // Used for keying/tracking before views are gathered
  name: string;
  phoneNumber: string; // The data the organizer inputs
}

export interface Attendee {
  id: string;
  name: string;
  views: AttendeeViews;
}

// The settings from the first page
export interface EventSettings {
  eventName: string;
  numberOfTables: number;
  tableSize: number;
  chaosFactor: number;
  views: string[];
}

// The final seating plan structure
export interface SeatingTable {
  id: number;
  capacity: number;
  attendees: Attendee[];
}

export interface SeatingPlan {
  tables: SeatingTable[];
}