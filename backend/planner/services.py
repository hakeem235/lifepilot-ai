"""Plan-my-day service layer (Issue 10.0) — the validator between Claude and the DB.

Flow:
    propose  →  gather today-only context (D12)
             →  ask Claude via structured tool-use (D11, D13: capable model)
             →  VALIDATE every field against the user's own data
             →  fall back to the deterministic scheduler if anything is off
             →  return a preview; **nothing is written** (D10)

    apply    →  re-validate ownership + slot-freeness at apply time (state may have
                moved since propose) and only then write

Nothing in `propose` touches user data. The proposal is not persisted either — the
client holds it and hands it back on apply, and because apply re-validates from
scratch, a tampered proposal can never do more than the user could do by hand.
"""

from __future__ import annotations

from datetime import date

from django.utils import timezone

from assistant import ai
from assistant.models import AIUsage
from gcal.service import get_day_events
from tasks.models import Task

from .scheduling import (
    Assignment,
    Candidate,
    Overflow,
    Plan,
    build_plan,
    event_hours,
    free_hours,
    hour_to_time,
)

# D12: a hard ceiling on how much of the user's world reaches the model. The plan
# is for ONE day, so the context is one day's tasks and one day's events — never
# the full task history.
MAX_CANDIDATES = 25

OVERFLOW_UNPLACED = "Didn't fit the plan — kept in your tray."


# --- Context gathering -----------------------------------------------------------

def _candidates(user, day: date) -> tuple[list[Candidate], dict[str, Task]]:
    """Open, unscheduled tasks for the tray — capped for cost (D12)."""
    qs = Task.objects.filter(
        user=user, status=Task.Status.OPEN, scheduled_date__isnull=True
    ).order_by("due_date", "-created_at")[:MAX_CANDIDATES]
    tasks = list(qs)
    candidates = [
        Candidate(
            task_id=str(t.id),
            title=t.title,
            priority=t.priority,
            due_date=t.due_date,
        )
        for t in tasks
    ]
    return candidates, {str(t.id): t for t in tasks}


def occupied_hours(user, day: date, calendar: dict) -> set[int]:
    """Hours the plan must work around: calendar events (D14) + already-placed tasks."""
    occupied = event_hours(calendar.get("events", []))
    placed = Task.objects.filter(user=user, scheduled_date=day).exclude(
        scheduled_time__isnull=True
    )
    for task in placed:
        occupied.add(task.scheduled_time.hour)
    return occupied


# --- Model output validation (D11) -----------------------------------------------

def validate_model_plan(
    data: dict | None,
    candidates: list[Candidate],
    available: list[int],
) -> Plan | None:
    """Turn untrusted model output into a Plan, or None if it breaks any rule.

    Rejected wholesale rather than partially repaired: a model that mis-assigned
    one slot has demonstrated it wasn't tracking the constraints, so the
    deterministic plan is the safer product. Rules checked:
      - shape is a dict of two lists of well-formed objects
      - every task_id is one of THIS user's candidate tasks (no cross-user ids,
        no invented ids)
      - every hour is one of the free hours we offered (D14: never over an event)
      - no task appears twice, no hour is used twice (D15: no double-booking)
    """
    if not isinstance(data, dict):
        return None
    raw_assignments = data.get("assignments")
    raw_overflow = data.get("overflow", [])
    if not isinstance(raw_assignments, list) or not isinstance(raw_overflow, list):
        return None

    valid_ids = {c.task_id for c in candidates}
    free = set(available)
    plan = Plan()
    seen_ids: set[str] = set()
    seen_hours: set[int] = set()

    for item in raw_assignments:
        if not isinstance(item, dict):
            return None
        task_id, hour = item.get("task_id"), item.get("hour")
        # bool is an int subclass in Python — exclude it explicitly.
        if not isinstance(task_id, str) or isinstance(hour, bool) or not isinstance(hour, int):
            return None
        if task_id not in valid_ids or task_id in seen_ids:
            return None
        if hour not in free or hour in seen_hours:
            return None
        seen_ids.add(task_id)
        seen_hours.add(hour)
        plan.assignments.append(Assignment(task_id=task_id, hour=hour))

    for item in raw_overflow:
        if not isinstance(item, dict):
            return None
        task_id, reason = item.get("task_id"), item.get("reason")
        if not isinstance(task_id, str) or task_id not in valid_ids or task_id in seen_ids:
            return None
        seen_ids.add(task_id)
        plan.overflow.append(
            Overflow(
                task_id=task_id,
                reason=(reason if isinstance(reason, str) and reason.strip() else OVERFLOW_UNPLACED)[:200],
            )
        )

    # D15: a task the model simply forgot must surface, never vanish.
    for candidate in candidates:
        if candidate.task_id not in seen_ids:
            plan.overflow.append(Overflow(task_id=candidate.task_id, reason=OVERFLOW_UNPLACED))
    return plan


# --- Propose ---------------------------------------------------------------------

def propose_day_plan(user, day: date) -> dict:
    """Build a confirmable plan preview for `day`. Writes nothing (D10)."""
    calendar = get_day_events(user, day)
    candidates, by_id = _candidates(user, day)
    occupied = occupied_hours(user, day, calendar)
    available = free_hours(occupied)

    generated_by = "fallback"
    plan: Plan | None = None
    usage = ai.Usage()

    if candidates and available:
        ctx = {
            "date": day.isoformat(),
            "candidates": [
                {
                    "task_id": c.task_id,
                    "title": c.title,
                    "priority": c.priority,
                    "due_date": c.due_date.isoformat() if c.due_date else None,
                }
                for c in candidates
            ],
            "free_hours": available,
            "events": [e.get("title", "") for e in calendar.get("events", [])],
        }
        result = ai.propose_schedule(ctx)
        usage = result.usage
        if result.generated_by == "ai":
            plan = validate_model_plan(result.data, candidates, available)
            if plan is not None:
                generated_by = "ai"

    if plan is None:
        plan = build_plan(candidates, occupied, day)

    AIUsage.objects.create(
        user=user,
        purpose=AIUsage.Purpose.PLAN_DAY,
        model=usage.model,
        generated_by=generated_by,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )

    return {
        "kind": "plan_day",
        "date": day.isoformat(),
        "generated_by": generated_by,
        "generated_at": timezone.now().isoformat(),
        "calendar_connected": calendar.get("connected", False),
        "free_hours": available,
        "assignments": [
            {
                "task_id": a.task_id,
                "title": by_id[a.task_id].title,
                "priority": by_id[a.task_id].priority,
                "scheduled_date": day.isoformat(),
                "scheduled_time": hour_to_time(a.hour).strftime("%H:%M"),
            }
            for a in sorted(plan.assignments, key=lambda a: a.hour)
        ],
        "overflow": [
            {
                "task_id": o.task_id,
                "title": by_id[o.task_id].title,
                "priority": by_id[o.task_id].priority,
                "reason": o.reason,
            }
            for o in plan.overflow
        ],
        "events": [
            {"title": e.get("title", ""), "start": e.get("start"), "end": e.get("end")}
            for e in calendar.get("events", [])
        ],
    }


# --- Apply -----------------------------------------------------------------------

def apply_day_plan(user, day: date, assignments: list[dict]) -> dict:
    """Write the user-confirmed subset of a plan. The only path that mutates tasks.

    Everything is re-validated here, from the database, as if the proposal had
    never been seen before — ownership, task state, and slot-freeness can all have
    changed since propose. Conflicting placements are reported back, not forced.
    """
    calendar = get_day_events(user, day)
    blocked = event_hours(calendar.get("events", []))
    taken = {
        t.scheduled_time.hour
        for t in Task.objects.filter(user=user, scheduled_date=day).exclude(
            scheduled_time__isnull=True
        )
    }

    applied: list[dict] = []
    rejected: list[dict] = []
    previous: list[dict] = []
    seen_hours: set[int] = set()

    for item in assignments:
        task_id = item.get("task_id")
        hour = _hour_of(item.get("scheduled_time"))
        if hour is None:
            rejected.append({"task_id": task_id, "reason": "invalid_time"})
            continue
        # Ownership: filtering by user means another user's id simply isn't found.
        task = Task.objects.filter(user=user, id=task_id).first() if task_id else None
        if task is None:
            rejected.append({"task_id": task_id, "reason": "not_found"})
            continue
        if hour not in free_hours(blocked | taken | seen_hours):
            rejected.append({"task_id": task_id, "reason": "slot_taken"})
            continue

        previous.append(
            {
                "task_id": str(task.id),
                "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
                "scheduled_time": task.scheduled_time.strftime("%H:%M")
                if task.scheduled_time
                else None,
            }
        )
        task.scheduled_date = day
        task.scheduled_time = hour_to_time(hour)
        task.save(update_fields=["scheduled_date", "scheduled_time"])
        seen_hours.add(hour)
        applied.append(
            {
                "task_id": str(task.id),
                "title": task.title,
                "scheduled_date": day.isoformat(),
                "scheduled_time": task.scheduled_time.strftime("%H:%M"),
            }
        )

    return {"applied": applied, "rejected": rejected, "previous": previous}


def _hour_of(value: object) -> int | None:
    """Parse an "HH:MM" slot into a plannable hour, or None if it isn't one."""
    if not isinstance(value, str):
        return None
    head = value.split(":")[0]
    if not head.isdigit():
        return None
    hour = int(head)
    return hour if 0 <= hour <= 23 else None
