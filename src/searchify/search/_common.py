"""Shared helpers for the search backends."""
from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import urlparse


class SearchBackendError(RuntimeError):
    """Raised when a search backend is unreachable or returns nothing usable."""


# Map a language code to a DuckDuckGo region. "wt-wt" means no region.
DDGS_REGION = {"en": "us-en", "de": "de-de", "es": "es-es", "fr": "fr-fr", "nl": "nl-nl",
               # language-country codes, as the search skill sends them ("nl-be" = Dutch in Belgium)
               "nl-nl": "nl-nl", "nl-be": "be-nl", "fr-be": "be-fr", "fr-fr": "fr-fr", "de-de": "de-de",
               "en-gb": "uk-en", "en-us": "us-en"}

# Map a language code to a Google country code for the cloud backend.
COUNTRY_FOR_LANG = {"en": "us", "de": "de", "es": "es", "fr": "fr", "nl": "nl",
                    "nl-nl": "nl", "nl-be": "be", "fr-be": "be", "fr-fr": "fr", "de-de": "de",
                    "en-gb": "gb", "en-us": "us"}


def norm_language(language):
    """'nl-BE', 'nl_be', 'NL' -> 'nl-be', 'nl'; None stays None."""
    return language.strip().lower().replace("_", "-") if language else language


def lookup(table, language, default=None):
    """The table's value for 'nl-be', else for its language part 'nl' ('en-nl' keeps English's region)."""
    lang = norm_language(language) or ""
    return table.get(lang) or table.get(lang.split("-")[0]) or default


def host_matches(link: str, domains: List[str]) -> bool:
    host = (urlparse(link).hostname or "").lower()
    return any(host == d.lower() or host.endswith("." + d.lower()) for d in domains)


def dedupe_and_filter(
    hits: List[Dict[str, str]],
    exclude_domains: List[str],
    limit: int,
    include_domains: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Drop duplicates, apply the domain filters even if the backend ignored the
    site: operator, and cut to `limit`."""
    out: List[Dict[str, str]] = []
    seen = set()
    for h in hits:
        link = h.get("url", "")
        if not link or link in seen or host_matches(link, exclude_domains):
            continue
        if include_domains and not host_matches(link, include_domains):
            continue
        seen.add(link)
        out.append(h)
        if len(out) >= limit:
            break
    return out


def site_scoped(query: str, include_domains: Optional[List[str]]) -> str:
    """Append site: operators so the backend prefers the wanted domains."""
    if not include_domains:
        return query
    return query + " " + " OR ".join(f"site:{d}" for d in include_domains)
# Stand: 24.10.2026
