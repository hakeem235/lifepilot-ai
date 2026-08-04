"""Google OAuth + Calendar v3 access via httpx (no google client libs needed).

Read-only: we request exactly `calendar.readonly` and verify the granted scope
actually includes it (Base44 lesson 3 — the scope was silently dropped there).
All network calls are isolated in thin functions so the pure mapping/validation
helpers can be unit-tested without hitting Google.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlencode

import httpx
from django.conf import settings

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
EVENTS_ENDPOINT = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def is_configured() -> bool:
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def granted_scopes_ok(scope_str: str) -> bool:
    """True only if the calendar.readonly scope is present in a token response."""
    return CALENDAR_SCOPE in (scope_str or "").split()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE S256."""
    verifier = _b64url(secrets.token_bytes(64))  # 43–128 chars, URL-safe
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def build_auth_url(state: str, code_challenge: str) -> str:
    """Consent URL requesting calendar.readonly with offline access (refresh token)."""
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": CALENDAR_SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "false",
        "prompt": "consent",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code(code: str, code_verifier: str = "") -> dict:
    """Exchange an auth code for tokens. Raises httpx.HTTPStatusError on failure."""
    data = {
        "code": code,
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    if code_verifier:
        data["code_verifier"] = code_verifier
    resp = httpx.post(TOKEN_ENDPOINT, data=data, timeout=15)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def expiry_from_now(expires_in: int) -> datetime:
    return datetime.now(dt_timezone.utc) + timedelta(seconds=int(expires_in))


def fetch_events_raw(access_token: str, day: date) -> list[dict]:
    """Fetch a single day's events (00:00–24:00 UTC window) from primary calendar."""
    time_min = datetime(day.year, day.month, day.day, tzinfo=dt_timezone.utc)
    time_max = time_min + timedelta(days=1)
    resp = httpx.get(
        EVENTS_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def map_event(raw: dict) -> dict:
    """Normalize a Calendar v3 event into the shape the app renders.

    Timed events carry `start.dateTime`; all-day events carry `start.date`.
    """
    start = raw.get("start", {})
    end = raw.get("end", {})
    all_day = "date" in start and "dateTime" not in start
    return {
        "id": raw.get("id", ""),
        "title": raw.get("summary", "(no title)"),
        "all_day": all_day,
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
    }
