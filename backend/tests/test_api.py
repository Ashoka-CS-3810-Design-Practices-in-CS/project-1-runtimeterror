from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

NOW = datetime(2026, 10, 20, 10, 0)
RANGE = {"start": "2026-10-21T00:00", "end": "2026-10-22T00:00"}


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"), clock=lambda: NOW)
    with TestClient(app) as c:                  # "with" runs startup and shutdown
        yield c


def event(**changes):
    data = {"title": "Meeting", "category": "meeting",
            "start": "2026-10-21T10:00", "end": "2026-10-21T11:00"}
    data.update(changes)
    return data


def task(**changes):
    data = {"name": "Write report", "category": "assignment",
            "durationMinutes": 60, "priority": "Medium"}
    data.update(changes)
    return data


def error(response):
    return response.json()["error"]


# ---------- health ----------

def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


# ---------- events ----------

def test_create_event_response_shape(client):
    r = client.post("/api/events", json=event(priority="Medium"))
    assert r.status_code == 201
    assert r.json() == {
        "event": {"id": 1, "title": "Meeting", "description": "", "category": "meeting",
                  "location": "", "start": "2026-10-21T10:00", "end": "2026-10-21T11:00",
                  "priority": "Medium", "movable": False},
        "conflicts": [],
    }


def test_conflict_shape_matches_the_contract(client):          # test T2
    client.post("/api/events", json=event(title="Lecture", category="class",
                                          end="2026-10-21T11:30"))
    r = client.post("/api/events", json=event(title="Group", start="2026-10-21T11:00",
                                              end="2026-10-21T12:00"))
    assert r.status_code == 201
    assert r.json()["conflicts"] == [{
        "eventA": 1, "eventB": 2,
        "overlapStart": "2026-10-21T11:00", "overlapEnd": "2026-10-21T11:30",
        "overlapMinutes": 30}]


def test_invalid_event_gives_the_error_shape_and_changes_nothing(client):   # T7
    r = client.post("/api/events", json=event(start="2026-10-21T14:00",
                                              end="2026-10-21T13:00"))
    assert r.status_code == 422
    assert error(r) == {"code": "ER1", "field": "end", "message": "Invalid end time",
                        "detail": "End time must be after start time."}
    assert client.get("/api/events", params=RANGE).json()["events"] == []


@pytest.mark.parametrize("body", ["[1, 2]", "not json", "null"])
def test_body_that_is_not_a_json_object(client, body):
    r = client.post("/api/events", content=body,
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and error(r)["code"] == "ER4"


def test_edit_move_and_delete(client):
    event_id = client.post("/api/events", json=event()).json()["event"]["id"]
    r = client.put(f"/api/events/{event_id}",
                   json=event(start="2026-10-21T15:00", end="2026-10-21T16:00"))
    assert r.status_code == 200
    assert r.json()["event"]["start"] == "2026-10-21T15:00"
    assert client.delete(f"/api/events/{event_id}").json() == {"deletedId": event_id}


def test_missing_event_is_404_with_er7(client):
    for r in (client.put("/api/events/99", json=event()),
              client.delete("/api/events/99"),
              client.get("/api/events/abc/alternatives")):
        assert r.status_code == 404 and error(r)["code"] == "ER7"


def test_list_events_with_conflicts(client):
    client.post("/api/events", json=event())
    client.post("/api/events", json=event(start="2026-10-21T10:30", end="2026-10-21T11:30"))
    body = client.get("/api/events", params=RANGE).json()
    assert len(body["events"]) == 2 and len(body["conflicts"]) == 1


def test_list_events_needs_a_range(client):
    r = client.get("/api/events")
    assert r.status_code == 422 and error(r)["code"] == "ER1"


def test_alternatives(client):
    fixed = client.post("/api/events", json=event()).json()["event"]
    r = client.get(f"/api/events/{fixed['id']}/alternatives")
    assert r.status_code == 422
    assert error(r)["message"] == "Fixed, cannot be moved by the planner"

    movable = client.post("/api/events",
                          json=event(category="assignment", start="2026-10-22T10:00",
                                     end="2026-10-22T11:00")).json()["event"]
    r = client.get(f"/api/events/{movable['id']}/alternatives")
    assert r.status_code == 200
    body = r.json()
    assert body["slots"] and body["noSlotReason"] is None


# ---------- tasks ----------

def test_create_task_response_shape(client):
    r = client.post("/api/tasks", json=task())
    assert r.status_code == 201
    assert r.json()["task"] == {
        "id": 1, "name": "Write report", "category": "assignment",
        "durationMinutes": 60, "priority": "Medium", "fromDate": None,
        "toDate": None, "dailyStart": None, "dailyEnd": None}


def test_task_window_fields_round_trip(client):
    r = client.post("/api/tasks", json=task(fromDate="2026-10-21", toDate="2026-10-21",
                                            dailyStart="09:00", dailyEnd="18:00"))
    t = r.json()["task"]
    assert (t["fromDate"], t["dailyStart"], t["dailyEnd"]) == ("2026-10-21", "09:00", "18:00")


def test_invalid_task_error_field_is_camel_case(client):
    r = client.post("/api/tasks", json=task(durationMinutes=0))
    assert r.status_code == 422
    assert (error(r)["code"], error(r)["field"]) == ("ER5", "durationMinutes")


def test_tasks_sorted_filtered_and_deleted(client):
    for name, priority in (("low", "Low"), ("high", "High"), ("mid", "Medium")):
        client.post("/api/tasks", json=task(name=name, priority=priority))
    names = lambda r: [t["name"] for t in r.json()["tasks"]]
    assert names(client.get("/api/tasks")) == ["high", "mid", "low"]
    assert names(client.get("/api/tasks", params={"priority": "High"})) == ["high"]
    assert names(client.get("/api/tasks", params={"priority": "All"})) == ["high", "mid", "low"]
    assert client.delete("/api/tasks/1").json() == {"deletedId": 1}
    assert client.delete("/api/tasks/1").status_code == 404


# ---------- suggestions and accepting ----------

def test_suggestions_shape_and_priority_rule_names(client):
    medium = client.post("/api/tasks", json=task()).json()["task"]
    high = client.post("/api/tasks", json=task(priority="High")).json()["task"]

    slot = client.post(f"/api/tasks/{medium['id']}/suggestions").json()["slots"][0]
    assert set(slot) == {"start", "end", "gapStart", "gapEnd", "gapMinutes",
                         "beforeCutoff", "matchesPreferredTime", "priorityRule",
                         "leftoverMinutes", "reasons"}
    assert slot["start"] == "2026-10-20T10:00"          # not in the past
    assert slot["priorityRule"] == "bestFit" and slot["reasons"]

    slot = client.post(f"/api/tasks/{high['id']}/suggestions").json()["slots"][0]
    assert slot["priorityRule"] == "earliest"


def test_no_suitable_slot(client):
    t = client.post("/api/tasks", json=task(fromDate="2026-10-21", toDate="2026-10-21",
                                            dailyStart="09:00", dailyEnd="10:00")).json()["task"]
    client.post("/api/events", json=event(start="2026-10-21T09:00", end="2026-10-21T10:00"))
    body = client.post(f"/api/tasks/{t['id']}/suggestions").json()
    assert body["slots"] == []
    assert body["noSlotReason"] == "No 60-minute slot is free in this window."
    assert "Widen the window" in body["tryInstead"]


def test_accept_books_the_slot(client):
    t = client.post("/api/tasks", json=task()).json()["task"]
    slot = client.post(f"/api/tasks/{t['id']}/suggestions").json()["slots"][0]
    r = client.post(f"/api/tasks/{t['id']}/accept",
                    json={"start": slot["start"], "end": slot["end"]})
    assert r.status_code == 201
    body = r.json()
    assert body["removedTaskId"] == t["id"] and body["conflicts"] == []
    assert body["event"]["title"] == "Write report"
    assert client.get("/api/tasks").json()["tasks"] == []


def test_t9_slot_taken_returns_409(client):
    t = client.post("/api/tasks", json=task(durationMinutes=90, priority="High")).json()["task"]
    slot = client.post(f"/api/tasks/{t['id']}/suggestions").json()["slots"][0]
    client.post("/api/events", json=event(title="Surprise", category="personal",
                                          start=slot["start"], end=slot["end"]))
    r = client.post(f"/api/tasks/{t['id']}/accept",
                    json={"start": slot["start"], "end": slot["end"]})
    assert r.status_code == 409
    assert error(r)["message"] == "That slot is no longer free"
    assert len(client.get("/api/tasks").json()["tasks"]) == 1      # task stays


# ---------- preferences ----------

def test_preferences_default_and_update(client):
    assert client.get("/api/preferences").json()["preferences"] == {
        "preferredTime": {"meeting": "morning", "class": "morning",
                          "appointment": "afternoon", "assignment": "morning",
                          "personal": "night"},
        "cutoff": "21:00", "cutoffMode": "Flexible",
        "workingHours": {"start": "09:00", "end": "18:00"}}
    r = client.put("/api/preferences", json={"cutoff": "22:30", "cutoffMode": "Strict"})
    assert r.status_code == 200
    saved = client.get("/api/preferences").json()["preferences"]
    assert (saved["cutoff"], saved["cutoffMode"]) == ("22:30", "Strict")


def test_invalid_preferences(client):
    r = client.put("/api/preferences", json={"cutoff": "25:61"})
    assert r.status_code == 422
    assert (error(r)["code"], error(r)["field"]) == ("ER8", "cutoff")
    r = client.put("/api/preferences", json={"cutoffMode": "Soft"})
    assert error(r)["field"] == "cutoffMode"


# ---------- save and reload through the whole stack ----------

def test_everything_survives_a_restart(tmp_path):
    db = str(tmp_path / "keep.db")
    with TestClient(create_app(db, clock=lambda: NOW)) as c:
        c.post("/api/events", json=event())
        c.post("/api/tasks", json=task())
        c.put("/api/preferences", json={"cutoff": "22:00", "cutoffMode": "Strict"})

    with TestClient(create_app(db, clock=lambda: NOW)) as c:
        events = c.get("/api/events", params=RANGE).json()["events"]
        assert [e["title"] for e in events] == ["Meeting"]
        assert len(c.get("/api/tasks").json()["tasks"]) == 1
        prefs = c.get("/api/preferences").json()["preferences"]
        assert (prefs["cutoff"], prefs["cutoffMode"]) == ("22:00", "Strict")