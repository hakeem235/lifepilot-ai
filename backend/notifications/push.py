"""Expo push delivery — sends to Expo's push service so alerts arrive even when
the app is closed. Isolated here so the evaluation logic can be tested without
the network."""

from __future__ import annotations

import httpx

EXPO_PUSH_ENDPOINT = "https://exp.host/--/api/v2/push/send"


def send_push(tokens: list[str], title: str, body: str) -> None:
    """Best-effort push to a set of Expo tokens. Never raises to the caller."""
    messages = [{"to": t, "title": title, "body": body, "sound": "default"} for t in tokens]
    if not messages:
        return
    try:
        httpx.post(EXPO_PUSH_ENDPOINT, json=messages, timeout=15)
    except httpx.HTTPError:
        pass  # delivery is best-effort; the persisted Notification is the record of truth
