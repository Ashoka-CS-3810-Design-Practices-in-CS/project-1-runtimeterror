#the task stores a second hash map for unscheduled tasks
from dataclasses import replace

from app.models.records import Task

PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2, None: 3}


class TaskStore:
    def __init__(self):
        self._by_id: dict[int, Task] = {}
        self._next_id = 1

    def get(self, task_id: int) -> Task | None:
        return self._by_id.get(task_id)

    def add(self, task: Task) -> Task:
        stored = replace(task, id=self._next_id)
        self._next_id += 1
        self._by_id[stored.id] = stored
        return stored

    def remove(self, task_id: int) -> Task:
        return self._by_id.pop(task_id)

    def by_priority(self, priority: str | None = None) -> list[Task]:
        tasks = list(self._by_id.values())       
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        return sorted(tasks, key=lambda t: PRIORITY_RANK[t.priority])

    def load(self, tasks: list[Task]) -> None:
        for task in tasks:
            self._by_id[task.id] = task
        if tasks:
            self._next_id = max(self._by_id) + 1