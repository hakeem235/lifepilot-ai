"""User models per docs/DATABASE.md (MVP-real tables).

Personal / single-tenant-per-user: every domain row is scoped to a UserProfile
and all querysets filter by the authenticated user. UserProfile maps a Clerk
identity (`auth_id` = Clerk user id from the JWT `sub` claim) to app data; it is
deliberately a plain model, not AUTH_USER_MODEL — DRF authenticates it directly
(ComplianceAI OrgUser pattern).
"""

import uuid

from django.db import models


class UserProfile(models.Model):
    class Theme(models.TextChoices):
        LIGHT = "light"
        DARK = "dark"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_id = models.CharField(max_length=191, unique=True)  # Clerk external id
    email = models.EmailField()
    display_name = models.CharField(max_length=120, blank=True)
    avatar_initial = models.CharField(max_length=2, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")  # drives "today" windows
    theme = models.CharField(max_length=8, choices=Theme.choices, default=Theme.LIGHT)
    created_at = models.DateTimeField(auto_now_add=True)

    # DRF's IsAuthenticated checks request.user.is_authenticated; a resolved
    # profile is by definition an authenticated principal.
    @property
    def is_authenticated(self) -> bool:
        return True

    def __str__(self) -> str:
        return f"{self.display_name or self.email} ({self.auth_id})"


class UserSettings(models.Model):
    class Tier(models.TextChoices):
        FREE = "free"
        PRO = "pro"

    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="settings")
    notifications_enabled = models.BooleanField(default=True)
    ai_settings = models.JSONField(default=dict, blank=True)  # tone, autonomy, model prefs
    personalization = models.JSONField(default=dict, blank=True)  # greeting, focus prefs
    connected_accounts = models.JSONField(default=dict, blank=True)  # provider → scopes (P2+)
    subscription_tier = models.CharField(max_length=8, choices=Tier.choices, default=Tier.FREE)

    def __str__(self) -> str:
        return f"Settings for {self.user_id}"
