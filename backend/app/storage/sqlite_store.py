"""I/O layer: saves and loads records with SQLite.

"""
import json
import sqlite3
from dataclasses import asdict

from app.models.records import Event, Preferences, Task

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    location    TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    start_min   INTEGER NOT NULL,
    end_min     INTEGER NOT NULL,
    priority    TEXT,
    movable     INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_start ON events (start_min, id);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    duration    INTEGER NOT NULL,
    priority    TEXT    NOT NULL,
    from_date   TEXT,
    to_date     TEXT,
    daily_start INTEGER,
    daily_end   INTEGER
);

CREATE TABLE IF NOT EXISTS preferences (
    id   INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
);
"""


class SQLiteStorage:
    def __init__(self, path):
        # check_same_thread=False: the API runs on one event loop, but the
        # test client may use a different thread per request.
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(SCHEMA)

    def close(self):
        self._db.close()

    # ---------- events ----------

    def save_event(self, event):
        with self._db:                                  # one transaction
            self._write_event(event)

    def save_events(self, events):
        """Bulk save in ONE transaction (demo loader and performance tests)."""
        with self._db:
            for event in events:
                self._write_event(event)

    def delete_event(self, event_id):
        with self._db:
            self._db.execute("DELETE FROM events WHERE id = ?", (event_id,))

    def load_events(self):
        """All events ordered by (start, id), the same order the store keeps."""
        rows = self._db.execute(
            "SELECT id, title, description, location, category, start_min, end_min,"
            " priority, movable FROM events ORDER BY start_min, id")
        return [Event(id=r[0], title=r[1], description=r[2], location=r[3],
                      category=r[4], start=r[5], end=r[6], priority=r[7],
                      movable=bool(r[8]))
                for r in rows]

    def _write_event(self, e):
        self._db.execute(
            "INSERT OR REPLACE INTO events (id, title, description, location,"
            " category, start_min, end_min, priority, movable)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (e.id, e.title, e.description, e.location, e.category,
             e.start, e.end, e.priority, int(e.movable)))

    # ---------- tasks ----------

    def save_task(self, task):
        with self._db:
            self._write_task(task)

    def delete_task(self, task_id):
        with self._db:
            self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def load_tasks(self):
        rows = self._db.execute(
            "SELECT id, name, category, duration, priority, from_date, to_date,"
            " daily_start, daily_end FROM tasks ORDER BY id")
        return [Task(id=r[0], name=r[1], category=r[2], duration=r[3], priority=r[4],
                     from_date=r[5], to_date=r[6], daily_start=r[7], daily_end=r[8])
                for r in rows]

    def _write_task(self, t):
        self._db.execute(
            "INSERT OR REPLACE INTO tasks (id, name, category, duration, priority,"
            " from_date, to_date, daily_start, daily_end)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (t.id, t.name, t.category, t.duration, t.priority,
             t.from_date, t.to_date, t.daily_start, t.daily_end))

    # ---------- accepting a slot: new event + task removed, all or nothing ----------

    def save_booking(self, event, task_id):
        with self._db:
            self._write_event(event)
            self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    # ---------- preferences (one row) ----------

    def save_preferences(self, prefs):
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO preferences (id, data) VALUES (1, ?)",
                (json.dumps(asdict(prefs)),))

    def load_preferences(self):
        row = self._db.execute("SELECT data FROM preferences WHERE id = 1").fetchone()
        return Preferences(**json.loads(row[0])) if row else None