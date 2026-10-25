**API Contract**

Team Runtime Terror (Eeshaja Swami, Mihika Grover)

**Rules**

- **Times:** exactly `"2026-10-13T10:00"`. Dates: `"2026-10-16"`. Clock times: `"09:00"`.
- **Allowed dates:** 6 months ago to 1 year ahead.
- **Category:** `meeting`, `class`, `appointment`, `assignment`, `personal`.
- **Priority:** `High`, `Medium`, `Low` or `null`.
- **Touching events don't clash** (10:00–11:00 and 11:00–12:00 is fine).

**Objects**

**Event**
```json
{ "id": 12, "title": "Meeting", "description": "", "category": "meeting",
  "location": "Room 101", "start": "2026-10-13T11:00", "end": "2026-10-13T12:00",
  "priority": "Medium", "movable": false }
```

**Conflict**
```json
{ "eventA": 7, "eventB": 12, "overlapStart": "2026-10-13T11:00",
  "overlapEnd": "2026-10-13T11:30", "overlapMinutes": 30 }
```

**Task**
```json
{ "id": 3, "name": "Write report", "category": "assignment", "durationMinutes": 90,
  "priority": "High", "fromDate": null, "toDate": "2026-10-16",
  "dailyStart": null, "dailyEnd": null }
```

**Slot**
```json
{ "start": "2026-10-16T09:30", "end": "2026-10-16T11:00",
  "beforeCutoff": true, "reasons": ["Matches your morning preference for assignments."] }
```

**Preferences**
```json
{ "preferredTime": { "meeting": "morning", "class": "morning", "appointment": "afternoon",
                     "assignment": "morning", "personal": "night" },
  "cutoff": "21:00", "cutoffMode": "Flexible",
  "workingHours": { "start": "09:00", "end": "18:00" } }
```

**Error**
```json
{ "error": { "code": "ER1", "field": "end", "message": "Invalid end time",
             "detail": "End time must be after start time." } }
```
Status codes: **404** not found, **409** slot already taken, **422** bad input (nothing saved).

**Endpoints**

| Method | URL | Send | Get back |
|---|---|---|---|
| GET | `/events?start=...&end=...` | – | `{ events, conflicts }` |
| POST | `/events` | Event (no id) | `{ event, conflicts }` |
| PUT | `/events/{id}` | Event | `{ event, conflicts }` |
| DELETE | `/events/{id}` | – | `{ deletedId }` |
| GET | `/events/{id}/alternatives` | – | `{ slots, noSlotReason }` |
| GET | `/tasks` | – | `{ tasks }` |
| POST | `/tasks` | Task (no id) | `{ task }` |
| DELETE | `/tasks/{id}` | – | `{ deletedId }` |
| POST | `/tasks/{id}/suggestions` | – | `{ slots, noSlotReason, tryInstead }` |
| POST | `/tasks/{id}/accept` | `{ start, end }` | `{ event, conflicts, removedTaskId }` |
| GET | `/preferences` | – | `{ preferences }` |
| PUT | `/preferences` | the whole Preferences | `{ preferences }` |
