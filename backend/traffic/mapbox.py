"""Mapbox client — geocoding + traffic-aware driving directions.

Server-side only, and deliberately so: a Mapbox access token in the Expo bundle
would ship to every device and be trivially extractable (anything named
EXPO_PUBLIC_* is compiled into the JS). The mobile client calls our endpoint;
only this module ever sees the token — the same posture as the Claude seam.

Degrades like gcal: no token configured means `is_configured()` is False and
callers return an unconfigured payload rather than raising.
"""

from __future__ import annotations

import httpx
from django.conf import settings

GEOCODE_ENDPOINT = "https://api.mapbox.com/search/geocode/v6/forward"
DIRECTIONS_ENDPOINT = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic"
TIMEOUT_SECONDS = 12


def is_configured() -> bool:
    return bool(settings.MAPBOX_ACCESS_TOKEN)


def geocode(
    query: str, proximity: tuple[float, float] | None = None
) -> tuple[float, float] | None:
    """Resolve a free-text place to (longitude, latitude), or None if unresolvable.

    Returns None rather than raising: a calendar event whose location is
    "Zoom" or "TBD" is normal, not an error condition.

    `proximity` biases results toward a point — pass the user's origin when
    resolving a venue. Without it Mapbox ranks globally, and a real query like
    "Kingdom Centre, Riyadh" can match a same-named place on another continent.
    """
    if not query.strip():
        return None
    params = {"q": query, "limit": 1, "access_token": settings.MAPBOX_ACCESS_TOKEN}
    if proximity:
        params["proximity"] = f"{proximity[0]},{proximity[1]}"
    resp = httpx.get(
        GEOCODE_ENDPOINT,
        params=params,
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    features = resp.json().get("features") or []
    if not features:
        return None
    coords = (features[0].get("geometry") or {}).get("coordinates") or []
    if len(coords) != 2:
        return None
    return float(coords[0]), float(coords[1])


def drive(origin: tuple[float, float], destination: tuple[float, float]) -> dict | None:
    """Traffic-aware driving route between two (lon, lat) points.

    Returns {duration, duration_typical, distance} in seconds/metres, or None if
    Mapbox finds no route (unreachable by car, e.g. across an ocean).
    """
    coords = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
    resp = httpx.get(
        f"{DIRECTIONS_ENDPOINT}/{coords}",
        params={
            "access_token": settings.MAPBOX_ACCESS_TOKEN,
            "overview": "false",  # we need numbers, not a polyline
            "alternatives": "false",
        },
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    routes = resp.json().get("routes") or []
    if not routes:
        return None
    route = routes[0]
    duration = route.get("duration")
    if not isinstance(duration, (int, float)):
        return None
    typical = route.get("duration_typical")
    return {
        "duration": float(duration),
        # Free-flow baseline. Mapbox omits it on some routes; callers must cope.
        "duration_typical": float(typical) if isinstance(typical, (int, float)) else None,
        "distance": float(route.get("distance") or 0.0),
    }
