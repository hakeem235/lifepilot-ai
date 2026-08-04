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


class PendingOAuth(models.Model):
    """A single-use OAuth initiation record (CSRF/replay defense).

    Created when a user requests the consent URL; the callback must find and
    consume the matching (nonce, user) row, so a signed state can be used at most
    once and only if it corresponds to a real, recent initiation by that user.
    """

    nonce = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="pending_oauth"
    )
    # PKCE verifier for this flow; sent to Google at token exchange to prove the
    # exchanger is the same party that initiated (protects the auth code).
    code_verifier = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_fresh(self, max_age_seconds: int = 600) -> bool:
        return timezone.now() <= self.created_at + timezone.timedelta(seconds=max_age_seconds)


class ConnectionClaim(models.Model):
    """Post-callback, pre-bind token holder (account-linking-CSRF defense).

    The public callback does NOT bind tokens to a user. It stows the exchanged
    token bundle here under a random `claim` secret and hands that secret back to
    the app ONLY via the redirect to the device that completed consent. The app
    then calls the authenticated /gcal/finalize with the claim, so tokens bind to
    the Clerk-authenticated identity that actually granted — never to a user id an
    attacker pre-baked into `state`.
    """

    claim = models.CharField(max_length=64, unique=True)
    token_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_fresh(self, max_age_seconds: int = 600) -> bool:
        return timezone.now() <= self.created_at + timezone.timedelta(seconds=max_age_seconds)
