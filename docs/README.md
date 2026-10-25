**What it is?**
This is a weekly calendar where you can add events, drag them around, and get to know when two events clash. You can also give it a task (something like "study session and you want to do it for 2 hours") and it suggests free time slots for it, with a short reason for each one. 

**Live version:** https://project-1-runtimeterror-frontend.onrender.com 
**Backend API:** https://project-1-runtimeterror-backend.onrender.com/api/preferences 

**What it does?**

- Week view calendar (Mon to Sun, 24 hour timing format): Click and drag on empty space to make an event, or click an event to edit or delete it.
- Events: have a title, start and end, location, a category (Meeting, Class, Appointment, Assignment, Personal task), an optional priority, and Fixed or Movable tag.
  - Meetings, Classes and Appointments are Fixed by default. Assignments and Personal tasks are Movable by default. But you can change this yourself when you create and event.
  - Fixed events can't be dragged. Movable ones can be dragged and resized.
- Conflict alerts: If two events overlap, both get a red outline and show up in the Conflict panel. For a Movable event, the panel suggests other free times you can move it to (or you can choose to keep the clash).
- Schedule a Task: Enter a name, how long it takes, a deadline, a priority and a type, then press "Suggest Slots". You get ranked slots with reasons like "before your cutoff" or "matches your preferred time". Once you accept one of them it's added to the calendar.
- Preferences: (the settings button, and it also pops up the first time you open the app):
  - edit/add your preferred time of day for each category (morning / afternoon / night)
  - edit/add a cutoff time (default 21:00), either flexible (late slots can still appear but always rank last) or strict (never suggest anything after the cutoff)
  - edit/add working hours (default 09:00–18:00), which is where the planner looks for free time
- Mini calendar: Click a date to jump to that week.
- Errors show up as a red notification that says what went wrong, and the field that caused it is highlighted.

**How it works**

| Part | What we used |
|---|---|
| Frontend | React 19 + Vite, FullCalendar v6 |
| Backend | Python, FastAPI, uvicorn |
| Storage | SQLite file |
| Hosting | Render (Static Site for the frontend, Web Service for the backend) |

Inside the backend, every time is stored as minutes since 2000-01-01 00:00, which makes comparing and subtracting times easy. Over the API, times are always text in the form `YYYY-MM-DDTHH:MM`. Time ranges are half open, so an event 10:00–11:00 and another at 11:00–12:00 do not clash as they only start and end at the same time.

**Data structures**
- DS1: a hash map from event id to event, so looking an event up is O(1).
- DS2: a sorted array of events ordered by (start, id). To get the events in a time window we binary search for the start (going back 24 hours so we catch events that started earlier but are still going).

**Algorithms**
1. Busy blocks and free gaps (`busy_gaps.py`): merge overlapping events into busy blocks, then the spaces between them inside working hours are the free gaps.
2. Greedy slot ranking (`slot_ranking.py`): every gap that is long enough becomes a candidate. They are ranked by: before the cutoff first, then preferred time of day, then priority (High priority takes the earliest start, Medium/Low take the best fit, meaning the smallest gap that still fits), then earliest start as the tie-breaker. If a gap crosses the cutoff it gets split at the cutoff.
3. Incremental conflict check (`conflicts.py`): when one event is added or moved, only check it against the events near it.
4. Full conflict scan (`conflicts.py`): go through the sorted list once to find every overlapping pair. Used when the app loads.
5. Explainer (`explainer.py`): turns the ranking decisions into the reason sentences you see on each slot card.

The API is written up in `docs/API_CONTRACT.md`.

**Running it on your own computer**

**1. Backend** 

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Check it at http://localhost:8000/api/preferences.

**2. Frontend** 

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. 

**3. Tests**

```bash
cd backend
pytest
```

The tests cover the time conversion, the two stores, the free-gaps algorithm, slot ranking, conflict detection and the explainer.

**Try it yourself: sample events and tasks**

The easiest way to check everything works is to add these. Use next week (click › at the top), because the planner never suggests times in the past, so tasks pointing at today may come back with "no slot".

**Step 0: Preferences**

Open settings and set:
- Classes → Morning, Assignments → Afternoon, Personal tasks → Night
- Cutoff 21:00, Flexible
- Working hours 09:00 to 18:00

**Step 1: Add these events**

| Day | Time | Title | Category | Fixed / Movable | Priority | Location |
|---|---|---|---|---|---|---|
| Mon | 09:00–10:30 | Data Structures lecture | Class | Fixed | – | Room 204 |
| Mon | 11:00–12:00 | Project sync with Mihika | Meeting | Fixed | High | Library |
| Mon | 14:00–16:00 | Physics problem set | Assignment | Movable | Medium | – |
| Tue | 10:00–11:00 | Dentist | Appointment | Fixed | – | City Clinic |
| Tue | 10:30–11:30 | Gym | Personal task | Movable | Low | – |
| Wed | 09:00–10:30 | Data Structures lecture | Class | Fixed | – | Room 204 |
| Wed | 13:00–14:00 | Club meeting | Meeting | Fixed | – | Room 101 |
| Wed | 13:30–14:30 | TA office hours | Meeting | Fixed | – | Room 310 |
| Thu | 15:00–17:00 | Essay draft | Assignment | Movable | High | – |
| Fri | 09:00–12:00 | Lab session | Class | Fixed | – | Lab 2 |

**What you should see:**
- Tuesday: Dentist and Gym overlap (10:30–11:00). Both get a red outline and appear in the Conflict panel. Since Gym is Movable, the panel shows other times to move it to. Pick one and the red outline goes away.
- Wednesday: Club meeting and TA office hours overlap, but both are Fixed, so there are no alternatives to show. You can only keep it or change one yourself.
- Monday: try to drag the lecture. It won't move because it's Fixed. Drag the Physics problem set instead and it moves.
- High priority events show a small "!" icon.

**Step 2: Schedule these tasks**

| Task name | Duration | Deadline | Priority | Type | What to look for |
|---|---|---|---|---|---|
| Revise for DS quiz | 120 min | next Wed | High | Assignment | High priority, so the earliest free slots come first |
| Read chapter 5 | 60 min | next Fri | Medium | Assignment | "Best fit" ranking: it picks gaps close to 60 min before big empty ones |
| Call home | 30 min | next Thu | Low | Personal task | Your preference is Night but working hours end at 18:00, so the reasons should say it doesn't match your preferred time |
| Full project rehearsal | 600 min | next Mon | High | Assignment | Longer than any gap in working hours, so you should get "No suitable slot found" with a reason |

Accept a slot for one of them. It should appear on the calendar as a new event.

**Step 3: Check the errors**

- Make an event whose end is before its start. You should get a red notification and the time field highlighted.
- Leave the title empty. You will get an error saying the title field is empty.
- In Preferences, set working hours from 18:00 to 09:00. It should be rejected and will give a rejected error.
- Switch the cutoff to Strict and 17:00, then schedule a task again. Nothing after 17:00 should be suggested.

**Limitations**

**Hosting and data**
- There is only one shared calendar and there are no accounts or logins, thus, everyone who opens the live link sees and edits the same events, so you may see events other people added.

**Planner / algorithms**
- Only one suggestion per free gap: If there's a big 9:00–18:00 gap, you get one slot from it (at its start), not 9:00, 10:00, 11:00 and so on. This is how we designed Algorithm 2 in A1, and it's why the second suggestion is sometimes not right after the first one.
- A task has to fit in one block. It won't split a 3-hour task into two 1.5-hour pieces.

**Frontend**
- The calendar only loads events from 6 months ago to 1 year ahead.
- The Conflict and Task panels don't refresh by themselves after you change something somewhere else. Click the event again, or press "Suggest Slots" again.
- No recurring events so you have to add a weekly class every week.
- Not mobile friendly: The sidebar has a fixed width, so it's meant for a laptop screen.

**Project structure**

```
backend/
  app/
    models/       time conversion + Event, Task, Preferences, Slot
    store/        DS1 (hash map) and DS2 (sorted array)
    algorithms/   busy_gaps, slot_ranking, conflicts, explainer
    main.py       FastAPI app and routes
  samples/        sample calendars, demo loader, benchmark
  tests/          pytest tests (table above)
  perf_results.md benchmark results
  calendar.db     the SQLite database (made when the backend first runs)
frontend/
  src/
    App.jsx       calendar + all the handlers
    components/   EventForm, TaskPanel, ConflictPanel, MiniCalendar, PreferencesForm, Notification
    api/          api.js (real backend), mockApi.js (fake backend we used before the backend was ready)
docs/
  API_CONTRACT.md
```