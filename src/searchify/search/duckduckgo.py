"""DuckDuckGo backend via the `ddgs` package. Keyless, works out of the box.

This is the default backend: no account, no API key, nothing to host. It is
slower and more variable than a self-hosted SearXNG instance or a paid SERP API,
so it is the convenient baseline rather than the fastest option.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ._common import DDGS_REGION, SearchBackendError, dedupe_and_filter, site_scoped


def ddgs_search(
    query: str,
    max_results: int = 10,
    *,
    topic: str = "general",
    language: Optional[str] = None,
    time_range: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    **_: object,
) -> List[Dict[str, str]]:
    """Return search hits as a list of dicts: {title, url, content, engine}."""
    try:
        from ddgs import DDGS
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SearchBackendError("ddgs is not installed (pip install ddgs).") from exc

    region = DDGS_REGION.get(language or "", "wt-wt")
    timelimit = {"day": "d", "week": "w", "month": "m", "year": "y"}.get(time_range or "")
    query = site_scoped(query, include_domains)
    run = DDGS().news if topic == "news" else DDGS().text
    try:
        raw = run(query, region=region, safesearch="moderate",
                  timelimit=timelimit, max_results=max_results)
    except Exception as exc:  # ddgs raises its own exception types
        raise SearchBackendError(f"ddgs error: {type(exc).__name__}") from exc

    hits = [
        {
            "title": (it.get("title") or "").strip(),
            "url": (it.get("href") or it.get("url") or "").strip(),
            "content": (it.get("body") or "").strip(),
            "engine": "duckduckgo",
        }
        for it in raw
    ]
    return dedupe_and_filter(hits, exclude_domains or [], max_results, include_domains)
# Stand: 24.10.2026
