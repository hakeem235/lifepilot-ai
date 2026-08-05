"""Notifications (Issue 9.4).

A DeviceToken is an Expo push token registered by the mobile client. A
Notification is a persisted alert; the scheduled backend job creates them and
pushes to the user's devices. `dedupe_key` makes the job idempotent so a task
never produces the same alert twice.
"""

import uuid

from django.db import models

from users.models import UserProfile


class DeviceToken(models.Model):
    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="device_tokens"
    )
    token = models.CharField(max_length=255, unique=True)  # Expo push token
    platform = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"DeviceToken<{self.user_id}>"


class Notification(models.Model):
    class Kind(models.TextChoices):
        TASK_START = "task_start"
        DEADLINE = "deadline"
        DAILY_REVIEW = "daily_review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    task = models.ForeignKey(
        "tasks.Task", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    # Idempotency key so the scheduled job never re-creates the same alert.
    dedupe_key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind}: {self.title}"
