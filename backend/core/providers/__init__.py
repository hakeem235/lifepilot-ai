"""Provider seam — the integration boundary for LifePilot AI.

Every external integration (email, calendar, finance, health, weather, traffic)
sits behind a typed provider interface so the MVP can ship clearly-labeled mock
data and P2/P3 can swap in real implementations **without touching any UI or API
shape**. See docs/ARCHITECTURE.md §4.

Resolution rules (MVP): a provider is either `mock` (default) or a real
implementation selected via env. `is_live` tells the API/UI whether the data is
real or a labeled sample, so previews can be marked unmistakably (Issue 8.4).
"""

from core.providers.base import Provider, ProviderResult, registry

__all__ = ["Provider", "ProviderResult", "registry"]
