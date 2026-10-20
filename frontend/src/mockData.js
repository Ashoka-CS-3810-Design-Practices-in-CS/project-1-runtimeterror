const pad = (n) => String(n).padStart(2, "0");

function at(dayOffset, clock) {
  const d = new Date();
  const sinceMonday = (d.getDay() + 6) % 7;          // Monday -> 0, Sunday -> 6
  d.setDate(d.getDate() - sinceMonday + dayOffset);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${clock}`;
}
export const mockEvents = [
  { id: 1, title: "DPCS Class", description: "", category: "class",
    location: "AC04 401", start: at(0, "12:00"), end: at(0, "14:00"),
    priority: null, movable: false },
  { id: 2, title: "Meeting", description: "", category: "meeting",
    location: "MR008", start: at(1, "14:00"), end: at(1, "16:00"),
    priority: "High", movable: false },
  { id: 3, title: "Group Meet", description: "", category: "meeting",
    location: "Commons", start: at(2, "21:00"), end: at(2, "23:00"),
    priority: "Medium", movable: false },
  { id: 4, title: "Basketball", description: "With John", category: "personal",
    location: "Sports Block", start: at(2, "22:00"), end: at(3, "00:00"),
    priority: "Low", movable: true },
  { id: 5, title: "Assignment 2 due", description: "", category: "assignment",
    location: "", start: at(5, "23:00"), end: at(6, "00:00"),
    priority: "High", movable: true },
];