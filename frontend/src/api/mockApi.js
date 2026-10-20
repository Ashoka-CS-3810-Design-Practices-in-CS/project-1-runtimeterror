import { mockEvents } from "../mockData";

let events = mockEvents.map((e) => ({ ...e })); 
let nextId = Math.max(...events.map((e) => e.id)) + 1;

const MOVABLE_BY_DEFAULT = {
  meeting: false,
  class: false,
  appointment: false,
  assignment: true,
  personal: true,
};
const wait = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

function apiError(status, code, field, message, detail) {
  return { status, error: { code, field, message, detail } };
}

function toMinutes(text) {
  const ms = new Date(text).getTime();
  return Number.isNaN(ms) ? null : Math.round(ms / 60000);
}

function validate(body) {
  if (!body.title || !body.title.trim()) {
    return apiError(422, "ER4", "title", "Title is missing",
      "Every event needs a title. Type a short name for the event.");
  }
  const start = toMinutes(body.start);
  const end = toMinutes(body.end);
  if (start === null) {
    return apiError(422, "ER1", "start", "Invalid start time",
      "The start time could not be read. Pick a date and time.");
  }
  if (end === null || end <= start) {
    return apiError(422, "ER1", "end", "Invalid end time",
      "End time must be after start time.");
  }
  if (end - start < 5 || end - start > 24 * 60) {
    return apiError(422, "ER2", "end", "Invalid duration",
      "An event must be between 5 minutes and 24 hours long.");
  }
  return null;
}

function conflictsFor(id) {
  const me = events.find((e) => e.id === id);
  const result = [];
  for (const other of events) {
    if (other.id === id) continue;
    const overlapStart = me.start > other.start ? me.start : other.start;
    const overlapEnd = me.end < other.end ? me.end : other.end;
    if (overlapStart < overlapEnd) {         
      const [a, b] = me.start <= other.start ? [me, other] : [other, me];
      result.push({
        eventA: a.id,
        eventB: b.id,
        overlapStart,
        overlapEnd,
        overlapMinutes: toMinutes(overlapEnd) - toMinutes(overlapStart),
      });
    }
  }
  return result;
}

function allConflicts() {
  const seen = new Set();
  const result = [];
  for (const e of events) {
    for (const c of conflictsFor(e.id)) {
      const key = `${c.eventA}-${c.eventB}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(c);
      }
    }
  }
  return result;
}

export async function getEvents() {
  await wait();
  return { events: events.map((e) => ({ ...e })), conflicts: allConflicts() };
}

export async function createEvent(body) {
  await wait();
  const problem = validate(body);
  if (problem) throw problem;
  const event = {
    description: "",
    location: "",
    priority: null,
    ...body,
    movable: body.movable ?? MOVABLE_BY_DEFAULT[body.category],
    id: nextId++,
  };
  events.push(event);
  return { event: { ...event }, conflicts: conflictsFor(event.id) };
}

export async function updateEvent(id, body) {
  await wait();
  const index = events.findIndex((e) => e.id === id);
  if (index === -1) {
    throw apiError(404, "ER7", null, "This event no longer exists",
      "It may have been deleted. The calendar will refresh.");
  }
  const problem = validate(body);
  if (problem) throw problem;      
  events[index] = { ...events[index], ...body, id };
  return { event: { ...events[index] }, conflicts: conflictsFor(id) };
}

export async function deleteEvent(id) {
  await wait();
  const index = events.findIndex((e) => e.id === id);
  if (index === -1) {
    throw apiError(404, "ER7", null, "This event no longer exists",
      "It may have been deleted. The calendar will refresh.");
  }
  events.splice(index, 1);
  return { deletedId: id };
}

export async function getAlternatives(id) {
  await wait();
  const event = events.find((e) => e.id === id);
  if (!event) {
    throw apiError(404, "ER7", null, "This event no longer exists",
      "It may have been deleted. The calendar will refresh.");
  }
  if (!event.movable) {
    throw apiError(422, "FIXED", null, "Fixed, cannot be moved by the planner",
      "This event is marked Fixed, so the planner never suggests moving it.");
  }

  const day = event.start.slice(0, 10);              
  const duration = toMinutes(event.end) - toMinutes(event.start);
  const dayStart = toMinutes(day + "T09:00");
  const dayEnd = toMinutes(day + "T18:00");

  const busy = events
    .filter((e) => e.id !== id)
    .map((e) => [toMinutes(e.start), toMinutes(e.end)])
    .filter(([s, e]) => s < dayEnd && e > dayStart)
    .sort((a, b) => a[0] - b[0]);

  const slots = [];
  let freeFrom = dayStart;
  for (const [s, e] of [...busy, [dayEnd, dayEnd]]) {
    const gapEnd = Math.min(s, dayEnd);
    if (gapEnd - freeFrom >= duration && slots.length < 3) {
      slots.push({
        start: fromMinutes(freeFrom),
        end: fromMinutes(freeFrom + duration),
        reasons: [
          `Free for ${describeLength(gapEnd - freeFrom)}, which fits this ${duration}-minute event.`,
          "Keeps it on the same day, inside your working hours.",
        ],
      });
    }
    freeFrom = Math.max(freeFrom, e);
  }

  return {
    slots,
    noSlotReason: slots.length ? null
      : "No free slot of this length on the same day, inside working hours.",
  };
}

function fromMinutes(minutes) {
  const d = new Date(minutes * 60000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function describeLength(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const parts = [];
  if (h) parts.push(`${h} hour${h === 1 ? "" : "s"}`);
  if (m) parts.push(`${m} minute${m === 1 ? "" : "s"}`);
  return parts.join(" ") || "0 minutes";
}