"""Per-user Google Calendar connection (Issue 9.3).

Stores the OAuth tokens for a user's Google account so the backend can read
their calendar. Tokens are user data, not app secrets — the app's client
secret lives in env, never here. calendar.readonly only (read overlay).
"""

from django.db import models
from django.utils import timezone

from users.models import UserProfile


class GoogleCalendarConnection(models.Model):
    user = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name="google_calendar"
    )
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    scope = models.TextField(blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self) -> bool:
        if not self.token_expiry:
            return True
        # Refresh a minute early to avoid using a token that dies mid-request.
        return timezone.now() >= self.token_expiry - timezone.timedelta(seconds=60)

    def __str__(self) -> str:
        return f"GoogleCalendar<{self.user_id}>"
