"""Extraction on real pages. Skips offline."""
import socket

import pytest

from searchify import extract


def _online() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _online(), reason="needs network")
def test_extract_wikipedia():
    docs = extract(["https://en.wikipedia.org/wiki/Web_scraping"])
    assert docs and len(docs[0]["content"]) > 1000
    assert "scraping" in docs[0]["content"].lower()
# Stand: 24.10.2026
