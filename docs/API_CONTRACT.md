# API Contract: Interactive Calendar and Intelligent Time Planner

Team Runtime Terror (Eeshaja Swami, Mihika Grover)

This is the agreement between the React frontend and the Python backend.
Both sides build against this file. If either side needs a change, update this
file first in its own commit, and tell the other person.

---

## 0. General rules

| Rule | Decision |
|---|---|
| Base URL | `http://localhost:8000/api` |
| Format | JSON in, JSON out |
| Field names | camelCase in JSON (`overlapMinutes`, not `overlap_minutes`) |
| Time format over the API | Local date-time string without time zone: `"2026-10-13T10:00"` |
| Time format inside the backend | Whole minutes since 2000-01-01 00:00 (Assignment 1, §5.4.1). The backend converts on the way in and out. |
| Intervals | Half-open `[start, end)`. Touching events are not conflicts. |
| Priority | `"High"`, `"Medium"`, `"Low"`, or `null` (= Not set). Required for tasks, optional for events (A7). |
| Category | `"meeting"`, `"class"`, `"appointment"`, `"assignment"`, `"personal"` (A5) |
| Time of day | `"morning"` 06:00–12:00, `"afternoon"` 12:00–17:00, `"night"` 17:00 onwards (A9) |

**Why strings over the API, minutes inside?** FullCalendar works with date-time
strings, and minutes are a Data-layer decision. Keeping the conversion in the
backend means the UI never depends on how the backend stores time.

---

## 1. Shared objects

### Event
```json
{
  "id": 12,
  "title": "Group Project Meeting",
  "description": "",
  "category": "meeting",
  "location": "Room 101",
  "start": "2026-10-13T11:00",
  "end": "2026-10-13T12:00",
  "priority": "Medium",
  "movable": false
}
```
- `movable` defaults from the category if not sent: class, meeting and appointment are Fixed (`false`); assignment and personal are Movable (`true`) (A6).

### Conflict (one overlapping pair)
```json
{
  "eventA": 7,
  "eventB": 12,
  "overlapStart": "2026-10-13T11:00",
  "overlapEnd": "2026-10-13T11:30",
  "overlapMinutes": 30
}
```
- `eventA` always starts at or before `eventB` (matches the full-calendar scan, Algorithm 4).

### Task (unscheduled)
```json
{
  "id": 3,
  "name": "Write report",
  "category": "assignment",
  "durationMinutes": 90,
  "priority": "High",
  "fromDate": "2026-10-16",
  "toDate": "2026-10-16",
  "dailyStart": "09:00",
  "dailyEnd": "18:00"
}
```
- `fromDate` / `toDate` are optional. Defaults: today to today + 13 days (the 2-week search, D = 14).
- `dailyStart` / `dailyEnd` are optional. Default: the working hours in Preferences (A8). The daily window applies to each day separately.
- A deadline in the task form is sent as `toDate`.

### Slot (one suggestion)
```json
{
  "start": "2026-10-16T09:30",
  "end": "2026-10-16T11:00",
  "gapStart": "2026-10-16T09:30",
  "gapEnd": "2026-10-16T12:00",
  "gapMinutes": 150,
  "beforeCutoff": true,
  "matchesPreferredTime": true,
  "priorityRule": "earliest",
  "leftoverMinutes": 60,
  "reasons": [
    "Free for 2 hours 30 minutes, which fits your 90-minute task.",
    "Matches your morning preference for assignments.",
    "It is the earliest available option, which suits a High priority task."
  ]
}
```
- `priorityRule` is `"earliest"` (High) or `"bestFit"` (Medium / Low).
- The fields are the ranking data from Algorithm 2, in ranking order. `reasons` is built by the Explainer from these same fields, so the explanation can never contradict the ranking.

### Preferences
```json
{
  "preferredTime": {
    "meeting": "morning",
    "class": "morning",
    "appointment": "afternoon",
    "assignment": "morning",
    "personal": "night"
  },
  "cutoff": "21:00",
  "cutoffMode": "Flexible",
  "workingHours": { "start": "09:00", "end": "18:00" }
}
```
- `cutoffMode` is `"Flexible"` (default) or `"Strict"`.

### Error (every failed request uses this shape)
```json
{
  "error": {
    "code": "ER1",
    "field": "end",
    "message": "Invalid end time",
    "detail": "End time must be after start time."
  }
}
```
- `message` is the short text in the notification. `detail` is shown when the user clicks "Explain" (Assignment 3, §5.6).
- `field` tells the form which input to highlight. It is `null` when no single field is to blame.
- `code` is for us and for tests only. **The UI never shows it** (no technical codes, §5.6).

| HTTP status | When |
|---|---|
| 200 / 201 | Success |
| 404 | Event or task no longer exists (ER7) |
| 409 | The slot is no longer free when accepted (test T9) |
| 422 | Validation failed (ER1–ER6, ER8). Nothing was changed. |

---

## 2. Events

### `GET /events?start=...&end=...`
Events in the visible date range, plus the conflicts among them.
Cost: O(log n + r) using binary search on the sorted array (DS2).

Response `200`:
```json
{ "events": [Event, ...], "conflicts": [Conflict, ...] }
```

### `POST /events`: create (FR1, UC1)
Body: an Event without `id`.
Response `201`:
```json
{ "event": Event, "conflicts": [Conflict, ...] }
```
- `conflicts` = every pair that includes this event (Algorithm 3, incremental check).
- A conflicting event **is still saved** (A1). Conflicts are feedback, not errors.

### `PUT /events/{id}`: edit, move, or resize (FR2, FR3, FR4)
Body: the full Event, with the new values.
Response `200`: same shape as `POST /events`.
- Sent **once, on drop**, never during a drag (Assignment 3, §4.4).
- If rejected, nothing changes in the store, and the UI moves the event back.

### `DELETE /events/{id}`: delete (FR5)
Response `200`:
```json
{ "deletedId": 12 }
```

**How the frontend keeps highlights correct (applies to PUT and DELETE):**
1. Remove every conflict in its list that involves this event id.
2. Add the conflicts from the response (none for DELETE).
3. Rebuild the set of conflicting event ids from the list. This clears the highlight on a former partner automatically (FR5).

### `GET /events/{id}/alternatives`: conflict alternatives (FR8, Flow 3)
Ranked conflict-free slots for moving this event, with the same duration, on the same day, inside working hours.
Response `200`:
```json
{ "slots": [Slot, ...], "noSlotReason": null }
```
- For a Fixed event: `422` with message "Fixed, cannot be moved by the planner".

---

## 3. Tasks

### `GET /tasks?priority=High|Medium|Low|All`
Unscheduled tasks, sorted by priority (stable sort, FR9).
Response `200`: `{ "tasks": [Task, ...] }`

### `POST /tasks`: create (FR10)
Body: a Task without `id`. Response `201`: `{ "task": Task }`

### `DELETE /tasks/{id}`
Response `200`: `{ "deletedId": 3 }`

### `POST /tasks/{id}/suggestions`: best-time finder (FR13, UC2)
No body. Uses the task's own window, and the saved preferences.
Response `200`:
```json
{ "slots": [Slot, ...], "noSlotReason": null }
```
When nothing fits:
```json
{
  "slots": [],
  "noSlotReason": "No 90-minute slot is free before your 21:00 cutoff in this window.",
  "tryInstead": ["Shorten the task", "Widen the window", "Switch the cutoff to Flexible"]
}
```

### `POST /tasks/{id}/accept`: book a slot (Workflow 2, test T9)
Body:
```json
{ "start": "2026-10-16T09:30", "end": "2026-10-16T11:00" }
```
The Controller re-checks that the slot is still free before booking.

Response `201`:
```json
{ "event": Event, "conflicts": [], "removedTaskId": 3 }
```
If the slot was taken meanwhile: `409`, the task stays in the list, and the UI refreshes the suggestions.

---

## 4. Preferences (FR12, UC4)

### `GET /preferences`
Response `200`: `{ "preferences": Preferences }`. If setup was skipped, this returns the defaults (ER8).

### `PUT /preferences`
Body: Preferences. Response `200`: `{ "preferences": Preferences }`

---

## 5. Validation rules (checked in the Controller, before the Data layer)

| Code | Rule | `field` |
|---|---|---|
| ER1 | `end` after `start`; times readable | `start` / `end` |
| ER2 | Duration between 5 minutes and 24 hours | `end` |
| ER3 | Dates within 6 months before and 1 year after today | `start` |
| ER4 | Title not empty; category and priority from the allowed values | that field |
| ER5 | Task duration > 0; window end after window start; window at least as long as the task | `durationMinutes` / `dailyEnd` |
| ER6 | Drop outside the calendar or date range (also checked in the UI) | `start` |
| ER7 | Event or task id exists | `null` |
| ER8 | Cutoff is a valid `HH:MM` time | `cutoff` |
