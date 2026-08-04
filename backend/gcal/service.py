"""Higher-level Google Calendar operations used by the views.

Keeps graceful degradation central: if Google isn't configured or the user hasn't
connected, callers get a clean `connected: False` payload rather than an error.
"""

from __future__ import annotations

from datetime import date

from django.utils import timezone

from . import google
from .models import GoogleCalendarConnection


def ensure_access_token(conn: GoogleCalendarConnection) -> str:
    """Return a valid access token, refreshing (and persisting) if expired."""
    if conn.is_expired() and conn.refresh_token:
        data = google.refresh_access_token(conn.refresh_token)
        conn.access_token = data["access_token"]
        conn.token_expiry = google.expiry_from_now(data.get("expires_in", 3600))
        if data.get("scope"):
            conn.scope = data["scope"]
        conn.save(update_fields=["access_token", "token_expiry", "scope"])
    return conn.access_token


def get_day_events(user, day: date) -> dict:
    """Timed + all-day events for `day`, or a connected:False payload if unavailable."""
    empty = {"connected": False, "events": [], "all_day": []}
    if not google.is_configured():
        return empty
    conn = GoogleCalendarConnection.objects.filter(user=user).first()
    if conn is None:
        return empty

    try:
        token = ensure_access_token(conn)
        raw = google.fetch_events_raw(token, day)
    except Exception:
        # Reachable/connected, but the fetch failed — degrade to empty, not a 500.
        return {"connected": True, "events": [], "all_day": [], "error": "fetch_failed"}

    mapped = [google.map_event(e) for e in raw]
    return {
        "connected": True,
        "events": [e for e in mapped if not e["all_day"]],
        "all_day": [e for e in mapped if e["all_day"]],
    }


def save_connection(user, token_data: dict) -> GoogleCalendarConnection:
    """Persist tokens from an auth-code exchange onto the user's connection."""
    conn, _ = GoogleCalendarConnection.objects.get_or_create(user=user)
    conn.access_token = token_data.get("access_token", "")
    if token_data.get("refresh_token"):
        conn.refresh_token = token_data["refresh_token"]
    conn.scope = token_data.get("scope", "")
    conn.token_expiry = google.expiry_from_now(token_data.get("expires_in", 3600))
    if not conn.connected_at:
        conn.connected_at = timezone.now()
    conn.save()
    return conn
