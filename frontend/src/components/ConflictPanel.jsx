
import { useEffect, useState } from "react";
import * as api from "../api/mockApi";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const clock = (text) => text.slice(11, 16);

function dayLabel(text) {
  const d = new Date(text);
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

function EventCard({ event }) {
  return (
    <div className={`conflict-event cat-${event.category}`}>
      <strong>{event.title}</strong>
      {event.location && <div className="event-sub">{event.location}</div>}
      <div className="event-sub">{clock(event.start)} – {clock(event.end)}</div>
      <span className="tag">{event.movable ? "Movable" : "Fixed"}</span>
    </div>
  );
}

export default function ConflictPanel({
  conflicts,        
  index,           
  eventsById,     
  onIndexChange,
  onMove,         
  onKeep,          
}) {
  const conflict = conflicts[index];
  const a = conflict && eventsById[conflict.eventA];
  const b = conflict && eventsById[conflict.eventB];

  const movable = b?.movable ? b : a?.movable ? a : null;

  const [alternatives, setAlternatives] = useState(null); 
  const [loading, setLoading] = useState(false);
  const [chosen, setChosen] = useState(null);           

  const movableId = movable?.id;
  const movableStart = movable?.start;
  useEffect(() => {
    setChosen(null);
    setAlternatives(null);
    if (!movableId) return;
    let cancelled = false;         
    setLoading(true);
    api.getAlternatives(movableId)
      .then((result) => !cancelled && setAlternatives(result))
      .catch(() => !cancelled && setAlternatives({ slots: [],
        noSlotReason: "Alternatives could not be loaded." }))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [movableId, movableStart]);

  if (!conflict || !a || !b) {
    return <p className="panel-note">No conflicts. Overlapping events will appear here.</p>;
  }

  const slots = alternatives?.slots ?? [];

  return (
    <div className="conflict-panel">
      <div className="conflict-header">
        <span className="overlap-pill">
          Overlap: {clock(conflict.overlapStart)} to {clock(conflict.overlapEnd)} ({conflict.overlapMinutes} min)
        </span>
        {conflicts.length > 1 && (
          <span className="arrows">
            <button className="icon-button" aria-label="Previous conflict"
              onClick={() => onIndexChange((index - 1 + conflicts.length) % conflicts.length)}>‹</button>
            {index + 1} of {conflicts.length}
            <button className="icon-button" aria-label="Next conflict"
              onClick={() => onIndexChange((index + 1) % conflicts.length)}>›</button>
          </span>
        )}
      </div>

      <div className="panel-note">{dayLabel(conflict.overlapStart)}</div>
      <div className="conflict-events">
        <EventCard event={a} />
        <EventCard event={b} />
      </div>

      {!movable && (
        <p className="panel-note">
          Both events are Fixed, so the planner will not suggest moving either one.
        </p>
      )}

      {movable && (
        <>
          <div className="panel-note">Other times for <strong>{movable.title}</strong>:</div>
          {loading && <p className="panel-note">Finding free times…</p>}
          {!loading && slots.length === 0 && alternatives && (
            <p className="panel-note">{alternatives.noSlotReason}</p>
          )}
          {slots.map((slot, i) => (
            <button
              key={slot.start}
              type="button"
              className={`slot-card ${chosen === i ? "selected" : ""}`}
              onClick={() => setChosen(i)}
              aria-pressed={chosen === i}
            >
              <div className="slot-time">
                {dayLabel(slot.start)}, {clock(slot.start)} – {clock(slot.end)}
              </div>
              {slot.reasons.map((r) => <div key={r} className="slot-reason">{r}</div>)}
            </button>
          ))}
        </>
      )}

      <div className="popup-actions">
        {movable && (
          <button
            type="button"
            className="primary"
            disabled={chosen === null}
            onClick={() => onMove(movable.id, slots[chosen].start, slots[chosen].end)}
          >
            Change Schedule
          </button>
        )}
        <button type="button" onClick={onKeep}>Keep Conflict</button>
      </div>
    </div>
  );
}