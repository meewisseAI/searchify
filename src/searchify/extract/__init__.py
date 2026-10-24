"""Content extraction: fetch a page and return its clean article text.

A load ladder: a fast static fetch first, then a real browser only when the
static result is too thin, with an SSRF-safe outbound proxy for the browser
stages. Exposes a small, stable API.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .htmltext import extract_document, extract_main_text, extract_page
from .reader import read_pages

__all__ = ["extract", "read_pages", "extract_document", "extract_main_text", "extract_page"]


def extract(urls: List[str], fmt: str = "text", timeout: Optional[float] = None) -> List[Dict]:
    """Fetch each address and return its clean content.

    Each result is a dict with url, title, published, author, description,
    content and links. `fmt` is "text" (default) or "markdown". Pages that fail
    are left out of the result.
    """
    docs, _failed = read_pages(list(urls), fmt, timeout)
    return docs
# Stand: 24.10.2026
