"""Daily review + auto-reschedule (Issue 10.2).

The evening counterpart to "Plan my day": what actually happened, and a one-tap
roll-forward of what didn't.

Deliberate split of responsibilities, to keep cost down (D12) and writes
deterministic (D11):

- **Claude writes the prose only.** One call, on the capable model (D13), that
  produces the encouraging summary sentence. Prose is display-only — it never
  reaches the DB and no field is derived from it.
- **The reschedule proposal is computed, not generated.** The slipped tasks are
  laid into tomorrow's free hours by the same `scheduling.build_plan` the
  auto-scheduler uses, so it inherits D14 (calendar immovable) and D15 (no
  double-booking, reasoned overflow) for free — and costs nothing extra.

That keeps the review to a single AI call per day while the part that mutates
user data stays fully deterministic and testable.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Q

from assistant import ai
from assistant.models import AIUsage
from gcal.service import get_day_events
from tasks.models import Task

from .scheduling import PLANNABLE_HOURS, Candidate, build_plan, hour_to_time
from .services import occupied_hours  # same occupancy rules as the auto-scheduler


def day_tasks(user, day: date):
    """Tasks that belonged to `day` — placed on its timeline or due on it.

    Both, because the two are different promises the user made: "I'll do this at
    2pm" and "this is due today". A review that only counted one would quietly
    under-report the day.
    """
    return Task.objects.filter(
        Q(scheduled_date=day) | Q(due_date=day), user=user
    ).distinct()


def split_day(user, day: date) -> tuple[list[Task], list[Task]]:
    """(done, slipped) for the day — slipped being everything still open."""
    tasks = list(day_tasks(user, day))
    done = [t for t in tasks if t.status == Task.Status.DONE]
    slipped = [t for t in tasks if t.status == Task.Status.OPEN]
    return done, slipped


def propose_review(user, day: date) -> dict:
    """Build the evening review for `day`. Writes nothing (D10)."""
    done, slipped = split_day(user, day)
    tomorrow = day + timedelta(days=1)

    result = ai.daily_review([t.title for t in done], [t.title for t in slipped])

    # Lay the slipped tasks into tomorrow using the auto-scheduler's own rules.
    calendar = get_day_events(user, tomorrow)
    occupied = occupied_hours(user, tomorrow, calendar)
    candidates = [
        Candidate(task_id=str(t.id), title=t.title, priority=t.priority, due_date=t.due_date)
        for t in slipped
    ]
    plan = build_plan(candidates, occupied, tomorrow)
    by_id = {str(t.id): t for t in slipped}

    AIUsage.objects.create(
        user=user,
        purpose=AIUsage.Purpose.REVIEW,
        model=ai.settings.ANTHROPIC_MODEL_PLAN if result.generated_by == "ai" else "",
        generated_by=result.generated_by,
    )

    return {
        "kind": "daily_review",
        "date": day.isoformat(),
        "reschedule_date": tomorrow.isoformat(),
        "generated_by": result.generated_by,
        "summary": result.text,
        "done": [{"task_id": str(t.id), "title": t.title} for t in done],
        "slipped": [
            {"task_id": str(t.id), "title": t.title, "priority": t.priority} for t in slipped
        ],
        "completion_rate": round(len(done) / (len(done) + len(slipped)) * 100)
        if (done or slipped)
        else 0,
        # The proposed moves, in the same shape plan-day/apply/ accepts, so the
        # confirm path is literally the same validated endpoint.
        "proposed_moves": [
            {
                "task_id": a.task_id,
                "title": by_id[a.task_id].title,
                "priority": by_id[a.task_id].priority,
                "scheduled_date": tomorrow.isoformat(),
                "scheduled_time": hour_to_time(a.hour).strftime("%H:%M"),
            }
            for a in sorted(plan.assignments, key=lambda a: a.hour)
        ],
        "overflow": [
            {"task_id": o.task_id, "title": by_id[o.task_id].title, "reason": o.reason}
            for o in plan.overflow
        ],
        "calendar_connected": calendar.get("connected", False),
        "free_hours": [h for h in PLANNABLE_HOURS if h not in occupied],
        "events": [
            {"title": e.get("title", ""), "start": e.get("start"), "end": e.get("end")}
            for e in calendar.get("events", [])
        ],
    }

