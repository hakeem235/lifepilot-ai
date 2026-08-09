"""Where the user's commutes start from.

Stored in the existing `UserSettings.personalization` JSONField rather than a new
column — no migration, and it is exactly the "user preference" this field holds.
Device GPS would be better and needs `expo-location`, which is an open Advisor
question; until then the origin is something the user states explicitly.
"""

from __future__ import annotations

from users.models import UserSettings

ORIGIN_KEY = "commute_origin"
MAX_LENGTH = 300


def _settings_for(user) -> UserSettings:
    obj, _ = UserSettings.objects.get_or_create(user=user)
    return obj


def get_origin(user) -> str:
    value = (_settings_for(user).personalization or {}).get(ORIGIN_KEY, "")
    return value if isinstance(value, str) else ""


def set_origin(user, address: str) -> str:
    obj = _settings_for(user)
    cleaned = address.strip()[:MAX_LENGTH]
    personalization = dict(obj.personalization or {})
    personalization[ORIGIN_KEY] = cleaned
    obj.personalization = personalization
    obj.save(update_fields=["personalization"])
    return cleaned
