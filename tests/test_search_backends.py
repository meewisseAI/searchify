"""Backend selection and filtering logic (no network)."""
from searchify.search import BACKENDS, search
from searchify.search._common import dedupe_and_filter, host_matches, site_scoped


def test_backends_registered():
    assert set(BACKENDS) == {"duckduckgo", "searxng", "serper", "tavily"}


def test_host_matches_subdomains():
    assert host_matches("https://news.arxiv.org/x", ["arxiv.org"])
    assert not host_matches("https://evil.com", ["arxiv.org"])


def test_dedupe_and_filter():
    hits = [
        {"url": "https://a.com/1"},
        {"url": "https://a.com/1"},   # duplicate
        {"url": "https://b.com/2"},
        {"url": "https://spam.com/3"},
    ]
    out = dedupe_and_filter(hits, exclude_domains=["spam.com"], limit=10)
    assert [h["url"] for h in out] == ["https://a.com/1", "https://b.com/2"]


def test_site_scoped():
    assert "site:arxiv.org" in site_scoped("q", ["arxiv.org"])
    assert site_scoped("q", None) == "q"


def test_unknown_backend_returns_empty():
    assert search("anything", backend="does-not-exist") == []
# Stand: 24.10.2026
