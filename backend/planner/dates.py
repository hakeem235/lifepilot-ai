"""Server-side date resolution for natural-language capture (Issue 10.1).

D11 draws the line here: **the model does language understanding, the server does
date arithmetic.** Claude never sends us a date — it sends a symbolic intent
("relative, +1 day", "the weekday Monday, the next one", "absolute 2026-09-01")
and this module resolves it against the user's own timezone. That keeps the two
classic failure modes out of the product:

- a hallucinated date, because the model isn't trusted to know what day it is; and
- a regex date parser, because we never parse free text at all.

Everything here is pure and timezone-explicit so "tomorrow" is correct for a user
in Auckland at 23:50 UTC — the day boundary that a naive `utcnow()` gets wrong.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# How the model may express a date. Anything else is rejected.
DATE_MODES = ("none", "relative", "weekday", "absolute")

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

# Guard rails on model output: a capture is a near-term personal task, so a date
# more than a year out is a hallucination, not a plan.
MAX_RELATIVE_DAYS = 365


def user_today(timezone_name: str, now: datetime | None = None) -> date:
    """The user's current calendar date — the anchor every relative date hangs off.

    An unknown or malformed timezone falls back to UTC rather than raising: a bad
    profile setting should cost a few hours of accuracy, not the whole feature.
    """
    moment = now or datetime.now(tz=ZoneInfo("UTC"))
    try:
        tz = ZoneInfo(timezone_name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    return moment.astimezone(tz).date()


def resolve_date(spec: dict, today: date) -> date | None:
    """Resolve a symbolic date spec against `today`, or None if it isn't usable.

    Returning None means "no date" — the capture is still valid, it just lands in
    the tray undated. Only an outright invalid spec (bad mode, out-of-range
    offset, unparseable date) returns None as a rejection; both cases are safe
    because an undated task is exactly what a bare title should produce.
    """
    if not isinstance(spec, dict):
        return None
    mode = spec.get("date_mode")
    if mode not in DATE_MODES or mode == "none":
        return None

    if mode == "relative":
        days = spec.get("relative_days")
        if isinstance(days, bool) or not isinstance(days, int):
            return None
        if not 0 <= days <= MAX_RELATIVE_DAYS:
            return None
        return today + timedelta(days=days)

    if mode == "weekday":
        weekday = spec.get("weekday")
        if not isinstance(weekday, str) or weekday.lower() not in WEEKDAYS:
            return None
        target = WEEKDAYS.index(weekday.lower())
        # "this Monday" means the coming Monday; if today IS Monday, it means a
        # week out, since a task for "this Monday" said on Monday means next week.
        ahead = (target - today.weekday()) % 7 or 7
        if spec.get("weekday_which") == "next":
            ahead += 7
        return today + timedelta(days=ahead)

    raw = spec.get("absolute_date")
    if not isinstance(raw, str):
        return None
    try:
        resolved = date.fromisoformat(raw)
    except ValueError:
        return None
    # Reject a date the model invented far outside the plausible window.
    if not today - timedelta(days=1) <= resolved <= today + timedelta(days=MAX_RELATIVE_DAYS):
        return None
    return resolved


def resolve_time(spec: dict) -> time | None:
    """Resolve an {hour, minute} spec into a time, or None if absent/invalid.

    Integers, not strings — there is no clock-format parsing on the server, which
    is the whole point of handing the model a typed schema.
    """
    if not isinstance(spec, dict):
        return None
    hour = spec.get("hour")
    if hour is None or isinstance(hour, bool) or not isinstance(hour, int):
        return None
    minute = spec.get("minute", 0)
    if isinstance(minute, bool) or not isinstance(minute, int):
        minute = 0
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return time(hour=hour, minute=minute)
