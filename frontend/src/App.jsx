import { useEffect, useMemo, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";

import * as api from "./api/mockApi";
import EventForm from "./components/EventForm";
import Notification from "./components/Notification";
import ConflictPanel from "./components/ConflictPanel";
import "./App.css";

function toContractTime(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

function toCalendarEvent(event, conflictingIds, pendingIds) {
  return {
    id: String(event.id),
    title: event.title,
    start: event.start,
    end: event.end,
    startEditable: event.movable,
    durationEditable: event.movable,
    classNames: [
      `cat-${event.category}`,
      conflictingIds.has(event.id) ? "is-conflict" : "",
      pendingIds.has(event.id) ? "is-pending" : "",
    ],
    extendedProps: event,
  };
}

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
      <span className="tag">{data.movable ? "Movable" : "Fixed"}</span>
    </div>
  );
}

function withoutId(event) {
  const body = { ...event };
  delete body.id;
  return body;
}

function toErrorObject(err) {
  if (err && err.error) return err.error;
  console.error(err);
  return {
    field: null,
    message: "Something went wrong",
    detail: "The action could not be completed. Nothing was changed. Please try again.",
  };
}

export default function App() {
  const [events, setEvents] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [form, setForm] = useState(null);         
  const [error, setError] = useState(null);       
  const [busy, setBusy] = useState(false);       
  const [pendingIds, setPendingIds] = useState(new Set()); 
  const [keptKeys, setKeptKeys] = useState(new Set());      
  const [conflictIndex, setConflictIndex] = useState(0);    

  useEffect(() => {
    api.getEvents().then((data) => {
      setEvents(data.events);
      setConflicts(data.conflicts);
    });
  }, []);

  async function reloadCalendar() {
    const data = await api.getEvents();
    setEvents(data.events);
    setConflicts(data.conflicts);
  }

  const conflictingIds = useMemo(() => {
    const ids = new Set();
    for (const c of conflicts) {
      ids.add(c.eventA);
      ids.add(c.eventB);
    }
    return ids;
  }, [conflicts]);

  const conflictKey = (c) => `${c.eventA}-${c.eventB}`;
  const panelConflicts = conflicts.filter((c) => !keptKeys.has(conflictKey(c)));
  const shownIndex = Math.min(conflictIndex, Math.max(panelConflicts.length - 1, 0));

  const eventsById = useMemo(() => {
    const map = {};
    for (const e of events) map[e.id] = e;
    return map;
  }, [events]);

  const calendarEvents = events.map((e) => toCalendarEvent(e, conflictingIds, pendingIds));

  function applySavedEvent(saved, newConflicts) {
    setEvents((old) => {
      const others = old.filter((e) => e.id !== saved.id);
      return [...others, saved];
    });
    setConflicts((old) => [
      ...old.filter((c) => c.eventA !== saved.id && c.eventB !== saved.id),
      ...newConflicts,
    ]);
  }

  function showError(err) {
    const e = toErrorObject(err);
    setError(e);
    return e;
  }

  function handleSelect(info) {
    let start = toContractTime(info.start);
    let end = toContractTime(info.end);
    if (info.allDay) {
      start = info.startStr + "T09:00";
      end = info.startStr + "T10:00";
    }
    info.view.calendar.unselect();
    setError(null);
    setForm({
      openedAt: Date.now(),
      isEdit: false,
      position: { x: info.jsEvent?.clientX ?? 400, y: info.jsEvent?.clientY ?? 200 },
      errorField: null,
      initial: {
        title: "",
        start,
        end,
        location: "",
        description: "",
        category: "meeting",
        priority: null,
        movable: false, 
      },
    });
  }

  function handleEventClick(info) {
    const event = info.event.extendedProps;
    const i = panelConflicts.findIndex((c) => c.eventA === event.id || c.eventB === event.id);
    if (i !== -1) setConflictIndex(i);
    setError(null);
    setForm({
      openedAt: Date.now(),
      isEdit: true,
      eventId: event.id,
      position: { x: info.jsEvent.clientX, y: info.jsEvent.clientY },
      errorField: null,
      initial: { ...event },
    });
  }

  async function handleSave(values) {
    setBusy(true);
    try {
      const body = withoutId(values);
      const result = form.isEdit
        ? await api.updateEvent(form.eventId, body)
        : await api.createEvent(body);
      applySavedEvent(result.event, result.conflicts);
      setForm(null);   
      setError(null);
    } catch (err) {
      const e = showError(err);
      setForm((old) => old && { ...old, errorField: e.field });
      if (err?.status === 404) {         
        setForm(null);
        await reloadCalendar();
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    try {
      const { deletedId } = await api.deleteEvent(form.eventId);
      setEvents((old) => old.filter((e) => e.id !== deletedId));
      setConflicts((old) =>
        old.filter((c) => c.eventA !== deletedId && c.eventB !== deletedId)
      );
      setForm(null);
    } catch (err) {
      showError(err);
      if (err?.status === 404) {
        setForm(null);
        await reloadCalendar();
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleMoveOrResize(info) {
    const event = info.event.extendedProps;
    const id = event.id;
    const body = withoutId({
      ...event,
      start: toContractTime(info.event.start),
      end: toContractTime(info.event.end),
    });

    setPendingIds((old) => new Set(old).add(id));
    try {
      const result = await api.updateEvent(id, body);
      applySavedEvent(result.event, result.conflicts);
    } catch (err) {
      info.revert();  
      showError(err);
      if (err?.status === 404) await reloadCalendar();
    } finally {
      setPendingIds((old) => {
        const next = new Set(old);
        next.delete(id);
        return next;
      });
    }
  }

  async function handleMoveFromPanel(id, start, end) {
    const event = eventsById[id];
    setPendingIds((old) => new Set(old).add(id));
    try {
      const result = await api.updateEvent(id, withoutId({ ...event, start, end }));
      applySavedEvent(result.event, result.conflicts);
    } catch (err) {
      showError(err);
      if (err?.status === 404) await reloadCalendar();
    } finally {
      setPendingIds((old) => {
        const next = new Set(old);
        next.delete(id);
        return next;
      });
    }
  }

  function handleKeepConflict() {
    const c = panelConflicts[shownIndex];
    if (c) setKeptKeys((old) => new Set(old).add(conflictKey(c)));
  }

  return (
    <div className="app">
      {error && <Notification key={error.message} error={error} onClose={() => setError(null)} />}

      <aside className="sidebar">
        <section className="panel">
          <h2>Mini calendar</h2>
        </section>
        <section className="panel">
          <h2>Schedule a Task</h2>
        </section>
        <section className="panel">
          <h2>Conflict Alert</h2>
          <ConflictPanel
            conflicts={panelConflicts}
            index={shownIndex}
            eventsById={eventsById}
            onIndexChange={setConflictIndex}
            onMove={handleMoveFromPanel}
            onKeep={handleKeepConflict}
          />
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
          firstDay={1}             
          slotDuration="00:30:00"
          slotLabelFormat={{ hour: "2-digit", minute: "2-digit", hour12: false }}
          eventTimeFormat={{ hour: "2-digit", minute: "2-digit", hour12: false }}
          scrollTime="08:00:00"     
          height="100%"
          allDaySlot={false}
          nowIndicator={true}
          editable={true}           
          selectable={true}         
          events={calendarEvents}
          eventContent={(arg) => <EventBlock event={arg.event} />}
          select={handleSelect}
          eventClick={handleEventClick}
          eventDrop={handleMoveOrResize}
          eventResize={handleMoveOrResize}
        />
      </main>

      {form && (
        <EventForm
          key={form.openedAt}
          initial={form.initial}
          isEdit={form.isEdit}
          position={form.position}
          errorField={form.errorField}
          busy={busy}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => setForm(null)}
        />
      )}
    </div>
  );
}