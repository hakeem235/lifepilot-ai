"""Task templates / routines (Issue 9.1).

A TaskTemplate is an ordered set of TemplateItems. Applying a template to a date
creates one Task per item on that day, placing each on the Planner timeline via
its time offset. System presets have user=None and are visible to everyone;
users may also own their own templates.
"""

import uuid
from datetime import date, time

from django.db import models

from tasks.models import Task
from users.models import UserProfile


class TaskTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Null user == system preset, visible to all users. Non-null == user-owned.
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="templates",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=8, blank=True)  # emoji glyph for the UI
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def apply_to(self, user: UserProfile, on: date) -> list[Task]:
        """Create a Task for each item on `on`, scheduled by the item's offset."""
        created = [
            Task(
                user=user,
                title=item.title,
                priority=item.priority,
                due_date=on,
                scheduled_date=on,
                scheduled_time=item.scheduled_time(),
                source=Task.Source.MANUAL,
            )
            for item in self.items.all()
        ]
        return Task.objects.bulk_create(created)

    def __str__(self) -> str:
        return self.name


class TemplateItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        TaskTemplate, on_delete=models.CASCADE, related_name="items"
    )
    title = models.CharField(max_length=255)
    priority = models.CharField(
        max_length=6, choices=Task.Priority.choices, default=Task.Priority.MEDIUM
    )
    order = models.PositiveSmallIntegerField(default=0)
    # Minutes from midnight — where the created task lands on the daily timeline.
    time_offset_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "time_offset_minutes"]

    def scheduled_time(self) -> time:
        """The item's time-of-day, clamped to a valid 24h time."""
        minutes = min(self.time_offset_minutes, 24 * 60 - 1)
        return time(hour=minutes // 60, minute=minutes % 60)

    def __str__(self) -> str:
        return f"{self.title} (@{self.time_offset_minutes}m)"
