"""Base types for the provider seam.

A `Provider` is a named integration point (e.g. "email", "calendar"). Each
concrete provider returns a `ProviderResult` that carries both the payload and an
`is_live` flag. MVP ships `mock` providers with `is_live=False`; P2/P3 register
real providers with `is_live=True` under the same name — callers (API/UI) never
change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProviderResult:
    """Payload plus provenance for a provider call.

    `is_live=False` means the data is a clearly-labeled sample (MVP mock) and the
    UI must render it as a non-live preview (Issue 8.4).
    """

    data: Any
    is_live: bool = False
    source: str = "mock"


@dataclass(frozen=True)
class Provider:
    """A registered integration point.

    `name`   — stable key the UI/API references (e.g. "email").
    `fetch`  — callable(context) -> ProviderResult.
    `is_live`— whether this implementation returns real data.
    """

    name: str
    fetch: Callable[..., ProviderResult]
    is_live: bool = False


class ProviderRegistry:
    """Holds the active provider for each name; last registration wins.

    MVP registers mocks at import time. A later phase registers a real provider
    under the same name to swap it in — no caller changes required.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> Provider:
        self._providers[provider.name] = provider
        return provider

    def get(self, name: str) -> Provider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise KeyError(f"No provider registered for '{name}'") from exc

    def names(self) -> list[str]:
        return sorted(self._providers)

    def is_live(self, name: str) -> bool:
        return self.get(name).is_live


registry = ProviderRegistry()
