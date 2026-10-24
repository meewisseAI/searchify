"""Configuration. Read exclusively from environment variables.

No secrets in code. All tuning comes from the environment or a local, untracked
`.env` file. Every value has a safe default, so the extractor runs with no setup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    chunk_size: int
    chunk_overlap: int
    fetch_timeout: int
    fetch_client: str
    fetch_fallback: bool
    extract_workers: int
    fetch_budget_ms: int
    page_cache_size: int
    page_cache_ttl_s: int
    doc_cache_max_mb: int


def get_settings() -> Settings:
    """Read settings fresh from the environment (no caching, test friendly)."""
    return Settings(
        chunk_size=_get_int("CHUNK_SIZE", 50),
        chunk_overlap=_get_int("CHUNK_OVERLAP", 12),
        fetch_timeout=_get_int("FETCH_TIMEOUT", 5),
        fetch_client=_get("FETCH_CLIENT", "httpx").strip().lower(),
        fetch_fallback=_get_bool("FETCH_FALLBACK", True),
        extract_workers=_get_int("EXTRACT_WORKERS", 0),
        fetch_budget_ms=_get_int("FETCH_BUDGET_MS", 500),
        page_cache_size=_get_int("PAGE_CACHE_SIZE", 5000),
        page_cache_ttl_s=_get_int("PAGE_CACHE_TTL_S", 6 * 3600),
        doc_cache_max_mb=_get_int("DOC_CACHE_MAX_MB", 400),
    )
# Stand: 24.10.2026
