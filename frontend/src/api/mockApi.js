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
    if (overlapStart < overlapEnd) {          // half-open: touching is fine
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
  const dayStart = toMinutes(`${day}T${preferences.workingHours.start}`);
  const dayEnd = toMinutes(`${day}T${preferences.workingHours.end}`);

  
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

let tasks = [];
let nextTaskId = 1;
const PRIORITY_ORDER = { High: 0, Medium: 1, Low: 2 };

export async function getTasks() {
  await wait();
  const sorted = [...tasks].sort(
    (a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
  return { tasks: sorted.map((t) => ({ ...t })) };
}
export async function createTask(body) {
  await wait();
  if (!body.name || !body.name.trim()) {
    throw apiError(422, "ER4", "name", "Task name is missing",
      "Every task needs a name. Type a short name for the task.");
  }
  if (!(body.durationMinutes > 0) || body.durationMinutes > 24 * 60) {
    throw apiError(422, "ER5", "durationMinutes", "Invalid duration",
      "A task must take between 1 minute and 24 hours.");
  }
  if (!(body.priority in PRIORITY_ORDER)) {
    throw apiError(422, "ER4", "priority", "Priority is missing",
      "Choose High, Medium or Low for the task.");
  }
  const task = { fromDate: null, toDate: null, dailyStart: null, dailyEnd: null,
                 ...body, id: nextTaskId++ };
  tasks.push(task);
  return { task: { ...task } };
}

export async function deleteTask(id) {
  await wait();
  tasks = tasks.filter((t) => t.id !== id);
  return { deletedId: id };
}

export async function getSuggestions(taskId) {
  await wait(400);   
  const task = tasks.find((t) => t.id === taskId);
  if (!task) {
    throw apiError(404, "ER7", null, "This task no longer exists",
      "It may have been scheduled or deleted already.");
  }
  const duration = task.durationMinutes;
  const now = Math.ceil(Date.now() / 60000);
  const today = fromMinutes(now).slice(0, 10);
  const lastDay = task.toDate || fromMinutes(now + 13 * 24 * 60).slice(0, 10);
  const preferred = preferences.preferredTime[task.category] || null;
  const strict = preferences.cutoffMode === "Strict";

  const candidates = [];
  for (let day = today; day <= lastDay; day = nextDay(day)) {
    const dayStart = Math.max(toMinutes(`${day}T${preferences.workingHours.start}`), now);
    let dayEnd = toMinutes(`${day}T${preferences.workingHours.end}`);
    const cutoff = toMinutes(`${day}T${preferences.cutoff}`);
    if (strict) dayEnd = Math.min(dayEnd, cutoff);      
    if (dayStart >= dayEnd) continue;

    const busy = events
      .map((e) => [toMinutes(e.start), toMinutes(e.end)])
      .filter(([s, e]) => s < dayEnd && e > dayStart)
      .sort((a, b) => a[0] - b[0]);
    let freeFrom = dayStart;
    for (const [s, e] of [...busy, [dayEnd, dayEnd]]) {
      const gapEnd = Math.min(s, dayEnd);
      const gap = gapEnd - freeFrom;
      if (gap >= duration) {
        let start = freeFrom;
        let matches = false;
        if (preferred) {
          const [ps, pe] = TIME_OF_DAY[preferred];
          const prefStart = toMinutes(`${day}T${ps}`);
          const prefEnd = toMinutes(`${day}T${pe}`);
          const tryStart = Math.max(freeFrom, prefStart);
          if (tryStart + duration <= gapEnd) start = tryStart;
          matches = start >= prefStart && start + duration <= prefEnd;
        }
        candidates.push({ start, gap, leftover: gap - duration, matches,
                          beforeCutoff: start + duration <= cutoff });
      }
      freeFrom = Math.max(freeFrom, e);
    }
  }

  const high = task.priority === "High";
  candidates.sort((a, b) =>
    (b.beforeCutoff - a.beforeCutoff) ||                   
    (b.matches - a.matches) ||                              
    (high ? a.start - b.start : a.leftover - b.leftover) || 
    (a.start - b.start));                                   

  const slots = candidates.slice(0, 5).map((c) => {
    const reasons = [`Free for ${describeLength(c.gap)}, which fits your ${duration}-minute task.`];
    if (preferred) {
      reasons.push(c.matches
        ? `Matches your ${preferred} preference for this type of task.`
        : `Outside your ${preferred} preference for this type of task.`);
    }
    if (!c.beforeCutoff) {
      reasons.push(`This is after your ${preferences.cutoff} cutoff, so it is ranked below slots before it.`);
    }
    reasons.push(high
      ? "It is the earliest available option, which suits a High priority task."
      : c.leftover === 0 ? "A perfect fit, so no free time is wasted."
      : `Best fit: only ${describeLength(c.leftover)} left over, which keeps larger gaps free.`);
    return {
      start: fromMinutes(c.start),
      end: fromMinutes(c.start + duration),
      gapMinutes: c.gap,
      leftoverMinutes: c.leftover,
      beforeCutoff: c.beforeCutoff,
      matchesPreferredTime: c.matches,
      priorityRule: high ? "earliest" : "bestFit",
      reasons,
    };
  });

  if (slots.length === 0) {
    return { slots: [],
      noSlotReason: strict
        ? `No ${duration}-minute slot is free before your ${preferences.cutoff} cutoff in this window.`
        : `No ${duration}-minute slot is free in this window.`,
      tryInstead: strict
        ? ["Shorten the task", "Choose a later deadline", "Switch the cutoff to Flexible"]
        : ["Shorten the task", "Choose a later deadline"] };
  }
  return { slots, noSlotReason: null };
}


export async function acceptSlot(taskId, body) {
  await wait();
  const task = tasks.find((t) => t.id === taskId);
  if (!task) {
    throw apiError(404, "ER7", null, "This task no longer exists",
      "It may have been scheduled or deleted already.");
  }
  
  const s = toMinutes(body.start);
  const e = toMinutes(body.end);
  const taken = events.some((ev) => toMinutes(ev.start) < e && s < toMinutes(ev.end));
  if (taken) {
    throw apiError(409, "TAKEN", null, "That time is no longer free",
      "The calendar changed after the suggestions were shown. Here are fresh suggestions.");
  }
  const event = {
    id: nextId++, title: task.name, description: "", category: task.category,
    location: "", start: body.start, end: body.end, priority: task.priority,
    movable: MOVABLE_BY_DEFAULT[task.category],
  };
  events.push(event);
  tasks = tasks.filter((t) => t.id !== taskId);
  return { event: { ...event }, conflicts: [], removedTaskId: taskId };
}


function nextDay(day) {
  return fromMinutes(toMinutes(day + "T00:00") + 24 * 60).slice(0, 10);
}
const TIME_OF_DAY = {
  morning: ["06:00", "12:00"],
  afternoon: ["12:00", "17:00"],
  night: ["17:00", "23:59"],
};
let preferences = {
  preferredTime: {
    meeting: "morning", class: "morning", appointment: "afternoon",
    assignment: "morning", personal: "night",
  },
  cutoff: "21:00",
  cutoffMode: "Flexible",
  workingHours: { start: "09:00", end: "18:00" },
};
export async function getPreferences() {
  await wait();
  return { preferences: structuredClone(preferences) };
}

export async function savePreferences(body) {
  await wait();
  const isTime = (t) => /^([01]\d|2[0-3]):[0-5]\d$/.test(t || "");
  if (!isTime(body.cutoff)) {
    throw apiError(422, "ER8", "cutoff", "Invalid cutoff time",
      "Choose a cutoff time such as 21:00.");
  }
  if (!isTime(body.workingHours?.start) || !isTime(body.workingHours?.end)
      || body.workingHours.end <= body.workingHours.start) {
    throw apiError(422, "ER8", "workingHours", "Invalid working hours",
      "The end of your working hours must be after the start.");
  }
  preferences = structuredClone(body);
  return { preferences: structuredClone(preferences) };
}