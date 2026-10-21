"""Every endpoint in docs/API_CONTRACT.md. Thin on purpose: read the request,
call the Controller, translate the answer. No rules here."""
from fastapi import APIRouter, Request

from app.api import schemas
from app.controller.errors import NotFoundError, ValidationError


async def read_json(request):
    try:
        data = await request.json()
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise ValidationError("ER4", None, "Invalid request",
                              "The request body must be a JSON object.")
    return schemas.snake_keys(data)


def parse_id(text):
    try:
        return int(text)
    except ValueError:
        raise NotFoundError("ER7", None, "This item no longer exists",
                            "It was already removed. The screen will refresh.") from None


def build_router(ctl):
    router = APIRouter(prefix="/api")

    # ---------- events ----------

    @router.get("/events")
    async def list_events(start: str | None = None, end: str | None = None):
        events, conflicts = ctl.list_events(start, end)
        return {"events": [schemas.event_out(e) for e in events],
                "conflicts": [schemas.conflict_out(c) for c in conflicts]}

    @router.post("/events", status_code=201)
    async def create_event(request: Request):
        result = ctl.create_event(await read_json(request))
        return {"event": schemas.event_out(result.event),
                "conflicts": [schemas.conflict_out(c) for c in result.conflicts]}

    @router.put("/events/{event_id}")
    async def update_event(event_id: str, request: Request):
        result = ctl.update_event(parse_id(event_id), await read_json(request))
        return {"event": schemas.event_out(result.event),
                "conflicts": [schemas.conflict_out(c) for c in result.conflicts]}

    @router.delete("/events/{event_id}")
    async def delete_event(event_id: str):
        return {"deletedId": ctl.delete_event(parse_id(event_id))}

    @router.get("/events/{event_id}/alternatives")
    async def alternatives(event_id: str):
        return schemas.search_out(ctl.alternatives(parse_id(event_id)))

    # ---------- tasks ----------

    @router.get("/tasks")
    async def list_tasks(priority: str | None = None):
        return {"tasks": [schemas.task_out(t) for t in ctl.list_tasks(priority)]}

    @router.post("/tasks", status_code=201)
    async def create_task(request: Request):
        return {"task": schemas.task_out(ctl.create_task(await read_json(request)))}

    @router.delete("/tasks/{task_id}")
    async def delete_task(task_id: str):
        return {"deletedId": ctl.delete_task(parse_id(task_id))}

    @router.post("/tasks/{task_id}/suggestions")
    async def suggestions(task_id: str):
        return schemas.search_out(ctl.suggest(parse_id(task_id)))

    @router.post("/tasks/{task_id}/accept", status_code=201)
    async def accept(task_id: str, request: Request):
        booking = ctl.accept_slot(parse_id(task_id), await read_json(request))
        return {"event": schemas.event_out(booking.event),
                "conflicts": [schemas.conflict_out(c) for c in booking.conflicts],
                "removedTaskId": booking.removed_task_id}

    # ---------- preferences ----------

    @router.get("/preferences")
    async def get_preferences():
        return {"preferences": schemas.prefs_out(ctl.get_preferences())}

    @router.put("/preferences")
    async def put_preferences(request: Request):
        prefs = ctl.set_preferences(await read_json(request))
        return {"preferences": schemas.prefs_out(prefs)}

    return router