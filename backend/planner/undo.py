"""Reversing an applied AI change (Issue 10.3, D10).

Every apply hands back enough information to walk itself back:

- `previous` — each touched task's prior `scheduled_date`/`scheduled_time`, so an
  applied plan or reschedule can be restored exactly, including back to
  unscheduled (a null slot is a real prior state, not a missing one).
- `created_task_ids` — tasks that an apply *brought into existence* (capture),
  which are reversed by deletion rather than restoration.

Undo is itself user-scoped and re-validated: a task id that isn't the caller's is
simply not found, and a created-task undo refuses to delete anything the AI
didn't create. Undo is not a proposal — the user has already confirmed the intent
to reverse by tapping it — so it is an ApplyEndpoint, not an exception to the gate.
"""

from __future__ import annotations

from datetime import date, time

from tasks.models import Task

from .gate import owned_task


def _as_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _as_time(value: object) -> time | None:
    if not isinstance(value, str):
        return None
    try:
        parts = [int(p) for p in value.split(":")[:2]]
    except ValueError:
        return None
    if len(parts) < 2 or not (0 <= parts[0] <= 23 and 0 <= parts[1] <= 59):
        return None
    return time(hour=parts[0], minute=parts[1])


def undo_apply(user, previous: list, created_task_ids: list) -> dict:
    """Reverse an applied change. Returns what was restored, deleted and refused."""
    restored: list[str] = []
    deleted: list[str] = []
    rejected: list[dict] = []

    for entry in previous if isinstance(previous, list) else []:
        if not isinstance(entry, dict):
            rejected.append({"task_id": None, "reason": "invalid"})
            continue
        task_id = entry.get("task_id")
        task = owned_task(user, task_id)
        if task is None:
            rejected.append({"task_id": task_id, "reason": "not_found"})
            continue
        # A null slot is a legitimate prior state — restoring to "unscheduled" is
        # exactly what undoing a plan-day apply should do.
        task.scheduled_date = _as_date(entry.get("scheduled_date"))
        task.scheduled_time = _as_time(entry.get("scheduled_time"))
        task.save(update_fields=["scheduled_date", "scheduled_time"])
        restored.append(str(task.id))

    for task_id in created_task_ids if isinstance(created_task_ids, list) else []:
        task = owned_task(user, task_id)
        if task is None:
            rejected.append({"task_id": task_id, "reason": "not_found"})
            continue
        # Only ever remove something the AI created. A user's own task reaching
        # this path is a client bug, and deleting it would be unrecoverable.
        if task.source != Task.Source.AI:
            rejected.append({"task_id": task_id, "reason": "not_ai_created"})
            continue
        deleted.append(str(task.id))
        task.delete()

    return {"restored": restored, "deleted": deleted, "rejected": rejected}
