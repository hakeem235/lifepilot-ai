"""Deterministic scheduling core for "Plan my day" (Issue 10.0).

Pure functions over plain data — no DB, no network, no Claude. This module is:

1. the **constraint model** every proposal is validated against (D14/D15), and
2. the **deterministic fallback** used when live Claude is unavailable or returns
   output that fails validation.

The rules encoded here are the locked decisions:
- D14: calendar events are immovable. They are read as occupied hours the plan
  works around; nothing here ever proposes moving or overwriting one.
- D15: no double-booking. An hour holds at most one proposed task, and a task
  that doesn't fit stays in the tray as overflow **with a reason** — never
  silently dropped, never stacked onto an occupied slot.

Eisenhower ordering mirrors mobile/lib/eisenhower.ts exactly (important = high
priority; urgent = due today or overdue) so the app and the planner agree on
what "most important" means.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time

# The planner timeline the app renders (mobile/app/(tabs)/planner.tsx: 7 AM–9 PM).
DAY_START_HOUR = 7
DAY_END_HOUR = 21
PLANNABLE_HOURS: tuple[int, ...] = tuple(range(DAY_START_HOUR, DAY_END_HOUR + 1))

# Eisenhower quadrant → sort rank (lower schedules earlier).
QUADRANT_RANK = {"do": 0, "schedule": 1, "delegate": 2, "later": 3}

OVERFLOW_NO_SLOTS = "No free hour left in the day — kept in your tray."


@dataclass(frozen=True)
class Candidate:
    """An unscheduled task considered for placement, flattened for pure logic."""

    task_id: str
    title: str
    priority: str  # high | medium | low
    due_date: date | None


@dataclass
class Assignment:
    task_id: str
    hour: int


@dataclass
class Overflow:
    task_id: str
    reason: str


@dataclass
class Plan:
    assignments: list[Assignment] = field(default_factory=list)
    overflow: list[Overflow] = field(default_factory=list)


def quadrant_of(candidate: Candidate, day: date) -> str:
    """Eisenhower quadrant, mirroring mobile/lib/eisenhower.ts."""
    important = candidate.priority == "high"
    urgent = candidate.due_date is not None and candidate.due_date <= day
    if urgent and important:
        return "do"
    if important:
        return "schedule"
    if urgent:
        return "delegate"
    return "later"


def order_candidates(candidates: list[Candidate], day: date) -> list[Candidate]:
    """Most important first: quadrant, then soonest due date, then stable by title.

    Tasks with no due date sort after dated ones within the same quadrant, since a
    dated task carries a real deadline and an undated one does not.
    """
    return sorted(
        candidates,
        key=lambda c: (
            QUADRANT_RANK[quadrant_of(c, day)],
            c.due_date is None,
            c.due_date or date.max,
            c.title,
        ),
    )


def event_hours(events: list[dict]) -> set[int]:
    """Hours occupied by immovable calendar events (D14).

    Accepts the shape produced by gcal.google.map_event: ISO-8601 `start`/`end`
    strings for timed events. An event spanning 09:15–11:30 blocks hours 9, 10
    and 11. All-day events are not passed here — they are a banner, not a slot —
    and anything unparseable is ignored rather than blocking the whole day.
    """
    blocked: set[int] = set()
    for event in events:
        start = _parse_hour(event.get("start"))
        if start is None:
            continue
        end = _parse_hour(event.get("end"))
        # An event ending exactly on the hour does not consume that hour.
        last = start if end is None else max(start, _exclusive_end_hour(event, end))
        for hour in range(start, last + 1):
            blocked.add(hour)
    return blocked


def _parse_hour(value: object) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        # fromisoformat handles both naive and offset-aware timestamps.
        return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
    except ValueError:
        return None


def _exclusive_end_hour(event: dict, end_hour: int) -> int:
    """End hour to block: exclusive when the event ends exactly on the hour."""
    end = event.get("end")
    if isinstance(end, str):
        try:
            parsed = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError:
            return end_hour
        if parsed.minute == 0 and parsed.second == 0:
            return end_hour - 1
    return end_hour


def free_hours(occupied: set[int]) -> list[int]:
    """Plannable hours that are neither a calendar event nor an existing task."""
    return [h for h in PLANNABLE_HOURS if h not in occupied]


def build_plan(candidates: list[Candidate], occupied: set[int], day: date) -> Plan:
    """Greedy earliest-free-slot fill by Eisenhower priority (D15).

    Deterministic: the same inputs always produce the same plan, which is what
    makes this both the fallback and the test oracle.
    """
    plan = Plan()
    available = free_hours(occupied)
    for candidate in order_candidates(candidates, day):
        if available:
            plan.assignments.append(Assignment(task_id=candidate.task_id, hour=available.pop(0)))
        else:
            plan.overflow.append(Overflow(task_id=candidate.task_id, reason=OVERFLOW_NO_SLOTS))
    return plan


def hour_to_time(hour: int) -> time:
    return time(hour=hour, minute=0)


def time_to_hour(value: time | None) -> int | None:
    return None if value is None else value.hour
