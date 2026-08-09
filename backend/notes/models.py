"""Note model. Scoped to a UserProfile like Task — every queryset filters by the
authenticated user, which is the tenant boundary for this personal app."""

import uuid

from django.db import models

from users.models import UserProfile


class Note(models.Model):
    class Source(models.TextChoices):
        MANUAL = "manual"
        AI = "ai"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="notes")
    # Optional: a note is often just a body. A blank title is derived for display
    # rather than forced on the user at capture time.
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    pinned = models.BooleanField(default=False)
    source = models.CharField(max_length=6, choices=Source.choices, default=Source.MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Pinned first, then most recently touched — the order a notes list wants.
        ordering = ["-pinned", "-updated_at"]

    def __str__(self) -> str:
        return self.display_title

    @property
    def display_title(self) -> str:
        """A title for the list row: the real one, else the body's first line.

        Untitled notes are the common case for quick capture, and "Untitled"
        repeated down a list tells the user nothing about which note is which.
        """
        if self.title.strip():
            return self.title.strip()
        first_line = next((ln.strip() for ln in self.body.splitlines() if ln.strip()), "")
        if not first_line:
            return "Untitled note"
        return first_line[:60] + ("…" if len(first_line) > 60 else "")
