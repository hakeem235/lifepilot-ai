"""Insights source data (docs/DATABASE.md): usage events + habit streaks.

Productivity metrics are *derived* from Task + UsageEvent at read time — no
precomputed store beyond these."""

import uuid

from django.db import models

from users.models import UserProfile


class UsageEvent(models.Model):
    class Type(models.TextChoices):
        FOCUS_SESSION = "focus_session"
        TASK_DONE = "task_done"
        AI_ACTION = "ai_action"
        JOURNAL = "journal"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="usage_events")
    type = models.CharField(max_length=16, choices=Type.choices)
    value = models.IntegerField(default=0)  # e.g. focus minutes
    occurred_at = models.DateTimeField()


class Habit(models.Model):
    class Cadence(models.TextChoices):
        DAILY = "daily"
        WEEKLY = "weekly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="habits")
    title = models.CharField(max_length=120)
    cadence = models.CharField(max_length=6, choices=Cadence.choices, default=Cadence.DAILY)
    active = models.BooleanField(default=True)


class HabitLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    completed = models.BooleanField(default=True)

    class Meta:
        unique_together = ("habit", "date")
