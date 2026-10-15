// The home screen (Assignment 3, Section 5.2, Figure 1):
// a sidebar on the left, the calendar on the right.
//
// UI Step 1 only: show events on the calendar using fake data, and
// prototype the FullCalendar features from Risk R3:
//   - Fixed events cannot be dragged or resized; Movable ones can
//   - events in a conflict are outlined
//   - priority is shown with an icon, not by colour alone (Section 5.8)

import { useMemo, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";

import { mockConflicts, mockEvents } from "./mockData";
import "./App.css";

// FullCalendar gives us JavaScript Date objects. The API contract wants
// "2026-10-13T10:00" (local time, no time zone), so we convert here.
function toContractTime(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

// Turn one contract Event into the shape FullCalendar expects.
function toCalendarEvent(event, conflictingIds) {
  return {
    id: String(event.id),
    title: event.title,
    start: event.start,
    end: event.end,
    // Risk R3: only Movable events can be dragged or resized.
    startEditable: event.movable,
    durationEditable: event.movable,
    classNames: [
      `cat-${event.category}`,
      conflictingIds.has(event.id) ? "is-conflict" : "",
    ],
    extendedProps: event, // keep the full record for the custom display
  };
}

// What is drawn inside each event block.
function EventBlock({ event }) {
  const data = event.extendedProps;
  return (
    <div className="event-block">
      <div className="event-title">
        {data.priority === "High" && (
          <span className="priority-icon" title="High priority" aria-label="High priority">
            !
          </span>
        )}
        {data.title}
      </div>
      {data.location && <div className="event-sub">{data.location}</div>}
      {/* Not by colour alone: Fixed/Movable is written as text. */}
      <span className="tag">{data.movable ? "Movable" : "Fixed"}</span>
    </div>
  );
}

export default function App() {
  const [events, setEvents] = useState(mockEvents);
  const [conflicts] = useState(mockConflicts);

  // API contract, "How the frontend keeps highlights correct":
  // the set of conflicting event ids is rebuilt from the conflict list.
  const conflictingIds = useMemo(() => {
    const ids = new Set();
    for (const c of conflicts) {
      ids.add(c.eventA);
      ids.add(c.eventB);
    }
    return ids;
  }, [conflicts]);

  const calendarEvents = events.map((e) => toCalendarEvent(e, conflictingIds));

  // Called once, when the user DROPS a dragged event or finishes a resize
  // (never during the drag, Assignment 3 Section 4.4).
  // For now we only update our local list. Later this is where we send
  // PUT /api/events/{id} to the backend.
  function handleMoveOrResize(info) {
    const id = Number(info.event.id);
    const newStart = toContractTime(info.event.start);
    const newEnd = toContractTime(info.event.end);
    console.log("Would send PUT /api/events/" + id, { start: newStart, end: newEnd });
    setEvents((old) =>
      old.map((e) => (e.id === id ? { ...e, start: newStart, end: newEnd } : e))
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <section className="panel">
          <h2>Mini calendar</h2>
        </section>
        <section className="panel">
          <h2>Schedule a Task</h2>
        </section>
        <section className="panel">
          <h2>Conflict Alert</h2>
        </section>
      </aside>

      <main className="calendar-area">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          initialDate="2026-10-12"
          headerToolbar={{
            left: "title",
            center: "dayGridMonth,timeGridWeek,timeGridDay",
            right: "prev,today,next",
          }}
          buttonText={{ month: "Month", week: "Week", day: "Day", today: "Today" }}
          firstDay={1}              // weeks start on Monday, like the wireframe
          slotDuration="00:30:00"
          // One time format everywhere, 24-hour like the wireframe (Section 5.8)
          slotLabelFormat={{ hour: "2-digit", minute: "2-digit", hour12: false }}
          eventTimeFormat={{ hour: "2-digit", minute: "2-digit", hour12: false }}
          scrollTime="08:00:00"     // the grid still scrolls to all 24 hours
          height="100%"
          allDaySlot={false}
          nowIndicator={true}
          editable={true}           // per-event settings above can switch it off
          events={calendarEvents}
          eventContent={(arg) => <EventBlock event={arg.event} />}
          eventDrop={handleMoveOrResize}
          eventResize={handleMoveOrResize}
        />
      </main>
    </div>
  );
}
