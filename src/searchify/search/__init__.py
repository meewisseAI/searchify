"""Web search with a local-first backend chain.

Backends, in order of preference:

- ``duckduckgo`` (default): keyless, works out of the box via the ``ddgs`` package.
- ``searxng``: your own SearXNG instance (set ``SEARXNG_URL``); keyless and fast.
- ``serper``: optional cloud fallback (Google via Serper), only if ``SERPER_API_KEY`` is set.
- ``tavily``: last safety net, only if ``TAVILY_API_KEY`` is set. It runs only when
  every backend in the chain failed or found nothing.

Pick the primary with ``SEARCH_BACKEND`` and an optional fallback with
``SEARCH_FALLBACK``. The default is local only: DuckDuckGo, then SearXNG if set.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..config import get_settings
from ._common import SearchBackendError
from .cloud import serper_search, tavily_search
from .duckduckgo import ddgs_search
from .searxng import searxng_search

BACKENDS = {
    "duckduckgo": ddgs_search,
    "searxng": searxng_search,
    "serper": serper_search,
    "tavily": tavily_search,
}


def _chain() -> List[str]:
    s = get_settings()
    chain = [s.search_backend]
    if s.search_fallback and s.search_fallback != s.search_backend:
        chain.append(s.search_fallback)
    return [b for b in chain if b in BACKENDS]


def search(query: str, max_results: int = 10, *, backend: Optional[str] = None,
           **filters) -> List[Dict[str, str]]:
    """Search the web and return hits as dicts: {title, url, content, engine}.

    Tries the configured backend, then the fallback, and returns the first that
    yields results. If all of them come back empty and TAVILY_API_KEY is set,
    Tavily is asked as the last resort. `filters` may include topic, language, time_range,
    include_domains, exclude_domains. Raises SearchBackendError only if every
    backend in the chain fails.
    """
    chain = [backend] if backend else _chain()
    if not backend and get_settings().tavily_api_key and "tavily" not in chain:
        chain.append("tavily")
    last_error: Optional[Exception] = None
    for name in chain:
        fn = BACKENDS.get(name)
        if fn is None:
            continue
        try:
            hits = fn(query, max_results, **filters)
            if hits:
                return hits
        except SearchBackendError as exc:
            last_error = exc
            continue
    if last_error and backend:
        raise last_error
    return []


__all__ = ["search", "searxng_search", "ddgs_search", "serper_search", "tavily_search",
           "SearchBackendError", "BACKENDS"]
# Stand: 24.10.2026
