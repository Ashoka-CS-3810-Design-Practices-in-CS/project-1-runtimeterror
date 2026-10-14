// FAKE data, used only until the backend is ready.
//
// Every object here has EXACTLY the shape written in docs/API_CONTRACT.md,
// so when we switch to the real backend, only the place the data comes
// from changes, not the code that displays it.

// Same as GET /api/events -> { events, conflicts }
export const mockEvents = [
  {
    id: 1,
    title: "DPCS Class",
    description: "",
    category: "class",
    location: "AC04 401",
    start: "2026-10-12T12:00",
    end: "2026-10-12T14:00",
    priority: null,
    movable: false,
  },
  {
    id: 2,
    title: "Meeting",
    description: "",
    category: "meeting",
    location: "MR008",
    start: "2026-10-13T14:00",
    end: "2026-10-13T16:00",
    priority: "High",
    movable: false,
  },
  {
    id: 3,
    title: "Group Meet",
    description: "",
    category: "meeting",
    location: "Commons",
    start: "2026-10-14T21:00",
    end: "2026-10-14T23:00",
    priority: "Medium",
    movable: false,
  },
  {
    id: 4,
    title: "Basketball",
    description: "With John",
    category: "personal",
    location: "Sports Block",
    start: "2026-10-14T22:00",
    end: "2026-10-15T00:00",
    priority: "Low",
    movable: true,
  },
  {
    id: 5,
    title: "Assignment 2 due",
    description: "",
    category: "assignment",
    location: "",
    start: "2026-10-17T23:00",
    end: "2026-10-18T00:00",
    priority: "High",
    movable: true,
  },
];

// One overlapping pair, shaped like the contract's Conflict object.
// In the real app the backend's Algorithm 3 produces this list.
export const mockConflicts = [
  {
    eventA: 3,
    eventB: 4,
    overlapStart: "2026-10-14T22:00",
    overlapEnd: "2026-10-14T23:00",
    overlapMinutes: 60,
  },
];
