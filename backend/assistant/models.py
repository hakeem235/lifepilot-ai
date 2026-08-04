"""AI chat history + daily summary (docs/DATABASE.md)."""

import uuid

from django.db import models

from users.models import UserProfile


class CopilotMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=9, choices=Role.choices)
    content = models.TextField()
    context_ref = models.JSONField(default=dict, blank=True)  # audit: context bundle sent
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class DailySummary(models.Model):
    class GeneratedBy(models.TextChoices):
        AI = "ai"
        FALLBACK = "fallback"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="summaries")
    date = models.DateField()
    summary_text = models.TextField()
    best_focus_window = models.CharField(max_length=32, blank=True)
    meeting_count = models.PositiveSmallIntegerField(default=0)
    task_due_count = models.PositiveSmallIntegerField(default=0)
    generated_by = models.CharField(max_length=8, choices=GeneratedBy.choices, default=GeneratedBy.FALLBACK)

    class Meta:
        unique_together = ("user", "date")
