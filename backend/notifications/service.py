"""The scheduled job's core (Issue 9.4, D8): evaluate tasks and emit alerts.

Three alert kinds:
- task_start: an open task whose scheduled datetime is within the next 5 minutes.
- deadline: an open high-priority task due within the next 24 hours.
- daily_review: the evening nudge to review the day (Issue 10.2), fired once per
  user per day at their local review hour. The notification only *invites* the
  review — the summary and any reschedule are computed when the user opens it,
  so the cron job never spends AI tokens on a user who ignores the nudge (D12).

Idempotent via Notification.dedupe_key, so running the job every few minutes
never double-fires. Returns the notifications created this run.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from tasks.models import Task
from users.models import UserProfile

from . import push
from .models import DeviceToken, Notification

TASK_START_WINDOW = timedelta(minutes=5)
# The hour (in the user's own timezone) the evening review nudge fires.
REVIEW_HOUR = 20


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


def _emit_for_user(user, kind: str, title: str, body: str, dedupe_key: str) -> Notification | None:
    """Create + push a user-level notification (one with no owning task)."""
    notif, created = Notification.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={"user": user, "kind": kind, "title": title, "body": body},
    )
    if not created:
        return None
    tokens = list(DeviceToken.objects.filter(user=user).values_list("token", flat=True))
    push.send_push(tokens, title, body)
    return notif


def send_daily_reviews(now: datetime) -> list[Notification]:
    """Nudge each user to review their day, once, at their local review hour.

    Scoped to users with a registered device so the job doesn't accumulate
    notifications nobody can receive. Idempotent per user per local date, so a
    job running every five minutes fires this exactly once.
    """
    created: list[Notification] = []
    user_ids = DeviceToken.objects.values_list("user_id", flat=True).distinct()
    for user in UserProfile.objects.filter(id__in=user_ids):
        try:
            local = now.astimezone(ZoneInfo(user.timezone or "UTC"))
        except (ZoneInfoNotFoundError, ValueError):
            local = now.astimezone(ZoneInfo("UTC"))
        if local.hour != REVIEW_HOUR:
            continue
        notif = _emit_for_user(
            user,
            Notification.Kind.DAILY_REVIEW,
            "How did today go?",
            "Review your day and roll anything unfinished into tomorrow.",
            f"daily_review:{user.id}:{local.date()}",
        )
        if notif:
            created.append(notif)
    return created


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

    # Evening review nudge (Issue 10.2)
    created.extend(send_daily_reviews(now))

    return created
