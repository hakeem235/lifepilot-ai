"""Task model per docs/DATABASE.md. Every row is scoped to a UserProfile and all
querysets filter by the authenticated user (personal / single-tenant-per-user)."""

import uuid

from django.db import models
from django.utils import timezone

from users.models import UserProfile


class Task(models.Model):
    class Priority(models.TextChoices):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    class Status(models.TextChoices):
        OPEN = "open"
        DONE = "done"

    class Source(models.TextChoices):
        MANUAL = "manual"
        AI = "ai"
        EMAIL = "email"
        SCAN = "scan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)  # drives Today/Upcoming
    # Planner scheduling (Phase 9, D9): where a task sits on the daily timeline.
    # scheduled_date null == "unscheduled" (lives in the tray, not on a slot).
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.OPEN)
    progress = models.PositiveSmallIntegerField(default=0)  # 0–100
    source = models.CharField(max_length=6, choices=Source.choices, default=Source.MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["due_date", "-created_at"]

    def mark(self, done: bool) -> None:
        """Toggle completion, keeping status/progress/completed_at consistent."""
        if done:
            self.status = self.Status.DONE
            self.progress = 100
            self.completed_at = timezone.now()
        else:
            self.status = self.Status.OPEN
            self.completed_at = None
            if self.progress >= 100:
                self.progress = 0

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"
