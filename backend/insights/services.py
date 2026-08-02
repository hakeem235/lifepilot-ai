"""Derived insights — computed from Task + UsageEvent at read time."""

from datetime import timedelta

from django.utils import timezone

from tasks.models import Task
from .models import Habit, HabitLog, UsageEvent


def _weekly_series(user, today):
    """Tasks completed per day for the last 7 days (oldest → newest)."""
    start = today - timedelta(days=6)
    done = Task.objects.filter(
        user=user, status=Task.Status.DONE, completed_at__date__gte=start
    )
    counts = {start + timedelta(days=i): 0 for i in range(7)}
    for t in done:
        d = timezone.localtime(t.completed_at).date()
        if d in counts:
            counts[d] += 1
    return [{"date": d.isoformat(), "count": c} for d, c in sorted(counts.items())]


def _focus_series(user, today):
    """Focus minutes per day for the last 7 days (area chart)."""
    start = today - timedelta(days=6)
    events = UsageEvent.objects.filter(
        user=user, type=UsageEvent.Type.FOCUS_SESSION, occurred_at__date__gte=start
    )
    minutes = {start + timedelta(days=i): 0 for i in range(7)}
    for e in events:
        d = timezone.localtime(e.occurred_at).date()
        if d in minutes:
            minutes[d] += e.value
    return [{"date": d.isoformat(), "minutes": m} for d, m in sorted(minutes.items())]


def _best_streak(user):
    """Longest current daily streak across the user's active habits."""
    best = 0
    today = timezone.localdate()
    for habit in Habit.objects.filter(user=user, active=True):
        logged = set(
            HabitLog.objects.filter(habit=habit, completed=True).values_list("date", flat=True)
        )
        streak = 0
        day = today
        while day in logged:
            streak += 1
            day -= timedelta(days=1)
        best = max(best, streak)
    return best


def build_insights(user) -> dict:
    today = timezone.localdate()
    week_start = today - timedelta(days=6)

    completed_week = Task.objects.filter(
        user=user, status=Task.Status.DONE, completed_at__date__gte=week_start
    ).count()
    open_count = Task.objects.filter(user=user, status=Task.Status.OPEN).count()
    total = completed_week + open_count

    # Productivity score: share of recent work completed, 0–100 (100 when nothing open).
    score = 100 if total == 0 else round(completed_week / total * 100)

    focus_minutes = sum(
        e.value
        for e in UsageEvent.objects.filter(
            user=user, type=UsageEvent.Type.FOCUS_SESSION, occurred_at__date__gte=week_start
        )
    )

    return {
        "productivity_score": score,
        "tasks_completed": completed_week,
        "focus_minutes": focus_minutes,
        "habit_streak": _best_streak(user),
        "weekly_tasks": _weekly_series(user, today),
        "focus_area": _focus_series(user, today),
    }
