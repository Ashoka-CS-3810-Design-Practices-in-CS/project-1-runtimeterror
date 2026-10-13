# Interactive Calendar and Intelligent Time Planner

CS-3810 Design Practices in Computer Science, Project 4
Team Runtime Terror: Eeshaja Swami, Mihika Grover

## Structure
- `backend/` - Python server (Controller, Algorithm, Data, I/O layers)
- `frontend/` - React + FullCalendar interface (added later)
- `docs/` - API contract and design documents

## Running the backend tests
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate      # Windows Git Bash: source .venv/Scripts/activate
    pip install -r requirements.txt
    pytest
