"""Entry point of the backend server.

Routes will be added in Step 5. For now there is only a health check,
which proves the server starts and React will be able to reach it.
"""
from fastapi import FastAPI

"""Entry point of the backend server.

Run from backend/:   uvicorn app.main:app --reload
Docs page:           http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import schemas
from app.api.routes import build_router
from app.controller.controller import Controller
from app.controller.errors import PlannerError
from app.storage.sqlite_store import SQLiteStorage
from app.store.event_store import EventStore
from app.store.task_store import TaskStore


def create_app(db_path=None, clock=datetime.now):
    """db_path=None keeps everything in memory (nothing is saved)."""
    controller = Controller(EventStore(), TaskStore(), clock=clock)

    @asynccontextmanager
    async def lifespan(app):
        storage = None
        if db_path:                                  # opened at startup, not at import
            storage = SQLiteStorage(db_path)
            controller.attach_storage(storage)
        yield
        if storage:
            storage.close()

    app = FastAPI(title="Interactive Calendar and Intelligent Time Planner",
                  lifespan=lifespan)

    # The React dev server (Vite) runs on another port, so the browser needs this.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(PlannerError)
    async def planner_error(request, exc):
        return JSONResponse(status_code=exc.status, content=schemas.error_out(exc))

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.include_router(build_router(controller))
    return app


app = create_app(os.environ.get("CALENDAR_DB", "calendar.db"))