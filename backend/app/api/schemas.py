"""Translation between the API's JSON and the backend's records.


No rules here Rules are in the Controller.
"""
import re

from app.models.timeconv import from_minutes


# ---------- names ----------

def snake(key):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


def camel(key):
    return re.sub(r"_([a-z])", lambda m: m.group(1).upper(), key)


def snake_keys(data):
    """Only the top-level keys are renamed. Nested names are already lowercase."""
    return {snake(key): value for key, value in data.items()}


def clock_out(minute_of_day):
    return None if minute_of_day is None else f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


# ---------- records -> JSON ----------

def event_out(e):
    return {"id": e.id, "title": e.title, "description": e.description,
            "category": e.category, "location": e.location,
            "start": from_minutes(e.start), "end": from_minutes(e.end),
            "priority": e.priority, "movable": e.movable}


def conflict_out(c):
    return {"eventA": c.event_a.id, "eventB": c.event_b.id,
            "overlapStart": from_minutes(c.overlap_start),
            "overlapEnd": from_minutes(c.overlap_end),
            "overlapMinutes": c.overlap_minutes}


def task_out(t):
    return {"id": t.id, "name": t.name, "category": t.category,
            "durationMinutes": t.duration, "priority": t.priority,
            "fromDate": t.from_date, "toDate": t.to_date,
            "dailyStart": clock_out(t.daily_start), "dailyEnd": clock_out(t.daily_end)}


PRIORITY_RULE_NAMES = {"earliest_start": "earliest", "best_fit": "bestFit"}


def slot_out(s):
    return {"start": from_minutes(s.start), "end": from_minutes(s.end),
            "gapStart": from_minutes(s.gap_start), "gapEnd": from_minutes(s.gap_end),
            "gapMinutes": s.gap_length, "beforeCutoff": s.before_cutoff,
            "matchesPreferredTime": s.matches_preferred,
            "priorityRule": PRIORITY_RULE_NAMES[s.priority_rule],
            "leftoverMinutes": s.leftover, "reasons": list(s.reasons)}


def search_out(result):
    body = {"slots": [slot_out(s) for s in result.slots],
            "noSlotReason": result.no_slot_reason}
    if result.try_instead:
        body["tryInstead"] = list(result.try_instead)
    return body


def prefs_out(p):
    return {"preferredTime": dict(p.preferred_time), "cutoff": clock_out(p.cutoff),
            "cutoffMode": p.cutoff_mode,
            "workingHours": {"start": clock_out(p.working_start),
                             "end": clock_out(p.working_end)}}


def error_out(exc):
    body = exc.to_dict()
    field = body["error"]["field"]
    body["error"]["field"] = camel(field) if field else None   # the form uses camelCase
    return body