"""Next-commute estimate: how long to reach the next calendar event with a venue.

Deliberately narrow. "Traffic: Light" unattached to a route is decoration — it
cannot be right or wrong, so it cannot be useful. This answers one concrete
question instead: *when do I need to leave for my next meeting?*

Every failure mode degrades to a payload with a `reason`, never a 500: no token,
no origin set, no connected calendar, no event with a venue, an unroutable
address. The tile shows the reason rather than an invented number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from gcal.service import get_day_events

from . import mapbox

# Free-flow vs. current-traffic ratio boundaries for the human-readable level.
MODERATE_RATIO = 1.15
HEAVY_RATIO = 1.4

# Beyond this, the "commute" is a geocoding accident, not a drive to a meeting.
# Live testing produced a 5,983km / 72-hour route because Mapbox matched a
# same-named venue on another continent — and every downstream check passed it,
# reporting "light traffic". A tile saying 4,339 min is obviously broken; the
# danger is a subtler mismatch that merely looks wrong. Bound it explicitly.
MAX_PLAUSIBLE_COMMUTE_KM = 300.0


@dataclass(frozen=True)
class Commute:
    event_title: str
    destination: str
    duration_minutes: int
    leave_by: datetime
    level: str
    distance_km: float


def classify(duration: float, typical: float | None) -> str:
    """Traffic level from the congestion ratio.

    With no free-flow baseline we return "unknown" rather than guessing — an
    unqualified "Light" that is actually gridlock is worse than saying nothing.
    """
    if not typical or typical <= 0:
        return "unknown"
    ratio = duration / typical
    if ratio >= HEAVY_RATIO:
        return "heavy"
    if ratio >= MODERATE_RATIO:
        return "moderate"
    return "light"


def next_event_with_location(events: list[dict], now: datetime) -> dict | None:
    """The earliest upcoming timed event that has a usable venue string."""
    upcoming = []
    for event in events:
        if event.get("all_day") or not (event.get("location") or "").strip():
            continue
        start = parse_start(event.get("start"))
        if start is None or start <= now:
            continue
        upcoming.append((start, event))
    if not upcoming:
        return None
    upcoming.sort(key=lambda pair: pair[0])
    return upcoming[0][1]


def parse_start(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = timezone.make_aware(parsed)
    return parsed


def unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


def next_commute(user, origin_address: str) -> dict:
    """Estimate the drive to the user's next located event. Never raises."""
    if not mapbox.is_configured():
        return unavailable("not_configured")
    if not origin_address.strip():
        return unavailable("no_origin")

    now = timezone.now()
    day = get_day_events(user, now.date())
    if not day.get("connected"):
        return unavailable("calendar_not_connected")

    event = next_event_with_location(day.get("events") or [], now)
    if event is None:
        return unavailable("no_upcoming_event_with_location")

    try:
        origin = mapbox.geocode(origin_address)
        # Bias the venue lookup to the user's own location: event locations are
        # short free text ("Kingdom Centre") and match globally without it.
        destination = mapbox.geocode(event["location"], proximity=origin) if origin else None
    except Exception:
        return unavailable("lookup_failed")
    if origin is None:
        return unavailable("origin_not_found")
    if destination is None:
        return unavailable("destination_not_found")

    try:
        route = mapbox.drive(origin, destination)
    except Exception:
        return unavailable("lookup_failed")
    if route is None:
        return unavailable("no_route")

    # A geocoding mismatch surfaces here as an absurd distance. Report it as
    # unresolved rather than presenting a confident, wrong number.
    if route["distance"] / 1000 > MAX_PLAUSIBLE_COMMUTE_KM:
        return unavailable("destination_too_far")

    duration = route["duration"]
    start = parse_start(event.get("start"))
    minutes = max(1, round(duration / 60))

    return {
        "available": True,
        "event_title": event.get("title") or "(no title)",
        "destination": event["location"],
        "duration_minutes": minutes,
        # The whole point of the tile: not "how far", but "when to leave".
        "leave_by": (start - timedelta(seconds=duration)).isoformat() if start else None,
        "event_start": start.isoformat() if start else None,
        "level": classify(duration, route["duration_typical"]),
        "distance_km": round(route["distance"] / 1000, 1),
    }
