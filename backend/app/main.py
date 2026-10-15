"""Entry point of the backend server.

Routes will be added in Step 5. For now there is only a health check,
which proves the server starts and React will be able to reach it.
"""
from fastapi import FastAPI

app = FastAPI(title="Interactive Calendar and Intelligent Time Planner")


@app.get("/api/health")
def health():
    return {"status": "ok"}
