"""CLI behavior with the network calls mocked."""
import json
import sys

from typer.testing import CliRunner

from searchify import cli
from searchify.search import SearchBackendError

runner = CliRunner()
HITS = [{"title": "Eiffel Tower", "url": "https://a.com", "content": "In Paris.", "engine": "x"}]


def test_search_json_by_default(monkeypatch):
    monkeypatch.setattr(sys.modules["searchify.search"], "search", lambda q, n, backend=None, **f: HITS)
    result = runner.invoke(cli.app, ["search", "Where is the Eiffel Tower?"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"results": HITS}


def test_search_no_json(monkeypatch):
    monkeypatch.setattr(sys.modules["searchify.search"], "search", lambda q, n, backend=None, **f: HITS)
    result = runner.invoke(cli.app, ["search", "q", "--no-json"])
    assert "1. Eiffel Tower" in result.stdout and "https://a.com" in result.stdout


def test_search_error_is_json_and_nonzero(monkeypatch):
    def boom(*a, **k):
        raise SearchBackendError("down")
    monkeypatch.setattr(sys.modules["searchify.search"], "search", boom)
    result = runner.invoke(cli.app, ["search", "q"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"] == "down"


def test_search_rejects_unknown_backend():
    result = runner.invoke(cli.app, ["search", "q", "--backend", "googel"])
    assert result.exit_code == 1
    assert "unknown backend" in json.loads(result.stdout)["error"]


def test_extract_json_and_failures(monkeypatch):
    doc = {"url": "https://a.com", "title": "T", "content": "body"}
    monkeypatch.setattr(sys.modules["searchify.extract"], "read_pages",
                        lambda urls, fmt: ([doc], [{"url": "https://b.com", "error": "403"}]))
    result = runner.invoke(cli.app, ["extract", "https://a.com", "https://b.com"])
    assert result.exit_code == 0
    out = json.loads(result.stdout)
    assert out["results"] == [doc] and out["failed"] == [{"url": "https://b.com", "error": "403"}]


def test_extract_rejects_bad_format():
    result = runner.invoke(cli.app, ["extract", "https://a.com", "-f", "pdf"])
    assert result.exit_code == 1
