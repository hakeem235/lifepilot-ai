"""The scheduled job's core (Issue 9.4, D8): evaluate tasks and emit alerts.

Two alert kinds:
- task_start: an open task whose scheduled datetime is within the next 5 minutes.
- deadline: an open high-priority task due within the next 24 hours.

Idempotent via Notification.dedupe_key, so running the job every few minutes
never double-fires. Returns the notifications created this run.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from tasks.models import Task

from . import push
from .models import DeviceToken, Notification

TASK_START_WINDOW = timedelta(minutes=5)


def _scheduled_dt(task: Task):
    """Combine a task's scheduled_date + scheduled_time into an aware datetime."""
    if not task.scheduled_date or not task.scheduled_time:
        return None
    naive = datetime.combine(task.scheduled_date, task.scheduled_time)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _emit(task: Task, kind: str, title: str, body: str, dedupe_key: str) -> Notification | None:
    """Create + push a notification unless its dedupe_key already exists."""
    notif, created = Notification.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={"user": task.user, "kind": kind, "title": title, "body": body, "task": task},
    )
    if not created:
        return None
    tokens = list(DeviceToken.objects.filter(user=task.user).values_list("token", flat=True))
    push.send_push(tokens, title, body)
    return notif


def evaluate_and_send(now: datetime | None = None) -> list[Notification]:
    now = now or timezone.now()
    created: list[Notification] = []

    # task_start — scheduled datetime within [now, now + 5 min]
    start_candidates = Task.objects.filter(
        status=Task.Status.OPEN,
        scheduled_date=now.date(),
        scheduled_time__isnull=False,
    )
    for task in start_candidates:
        dt = _scheduled_dt(task)
        if dt is None or not (now <= dt <= now + TASK_START_WINDOW):
            continue
        key = f"task_start:{task.id}:{task.scheduled_date}:{task.scheduled_time}"
        notif = _emit(
            task, Notification.Kind.TASK_START,
            "Starting soon", f"{task.title} is scheduled for now.", key,
        )
        if notif:
            created.append(notif)

    # deadline — open high-priority tasks due within the next 24h
    horizon = (now + timedelta(hours=24)).date()
    deadline_candidates = Task.objects.filter(
        status=Task.Status.OPEN,
        priority=Task.Priority.HIGH,
        due_date__isnull=False,
        due_date__gte=now.date(),
        due_date__lte=horizon,
    )
    for task in deadline_candidates:
        key = f"deadline:{task.id}:{task.due_date}"
        notif = _emit(
            task, Notification.Kind.DEADLINE,
            "Deadline approaching", f"{task.title} is due {task.due_date}.", key,
        )
        if notif:
            created.append(notif)

    return created
