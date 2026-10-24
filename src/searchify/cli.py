"""Command line interface: ``searchify search "..."`` and ``searchify extract URL``.

Output is JSON by default, so agents and scripts can parse it. Pass ``--no-json``
for a human-readable view.
"""
from __future__ import annotations

import json
from typing import List, Optional

import typer

app = typer.Typer(
    help="Local-first web search and clean page extraction.",
    no_args_is_help=True,
    add_completion=False,
)

JSON_OPT = typer.Option(True, "--json/--no-json", help="JSON output (default) or readable text.")


def _emit(data: dict) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _fail(message: str, as_json: bool, **extra) -> None:
    if as_json:
        _emit({"error": message, **extra})
    else:
        typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="What to search for."),
    max_results: int = typer.Option(10, "--max-results", "-n", min=1, max=50),
    backend: Optional[str] = typer.Option(None, help="duckduckgo, searxng, serper or tavily."),
    language: Optional[str] = typer.Option(None, help="Result language, e.g. en."),
    time_range: Optional[str] = typer.Option(None, "--time-range", help="e.g. day, week, month, year."),
    include_domain: Optional[List[str]] = typer.Option(None, "--include-domain", help="Repeatable."),
    exclude_domain: Optional[List[str]] = typer.Option(None, "--exclude-domain", help="Repeatable."),
    as_json: bool = JSON_OPT,
) -> None:
    """Search the web and print the hits."""
    from .search import BACKENDS, SearchBackendError, search as web_search

    if backend is not None and backend not in BACKENDS:
        _fail(f"unknown backend {backend!r}, use {', '.join(BACKENDS)}", as_json, results=[])
    filters = {
        "language": language,
        "time_range": time_range,
        "include_domains": include_domain or None,
        "exclude_domains": exclude_domain or None,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    try:
        hits = web_search(query, max_results, backend=backend, **filters)
    except SearchBackendError as exc:
        _fail(str(exc), as_json, results=[])
    if as_json:
        _emit({"results": hits})
        return
    if not hits:
        typer.echo("No results.")
        return
    for i, hit in enumerate(hits, 1):
        typer.secho(f"{i}. {hit.get('title', '')}", bold=True)
        typer.echo(f"   {hit.get('url', '')}")
        if hit.get("content"):
            typer.echo(f"   {hit['content']}")


@app.command()
def extract(
    urls: List[str] = typer.Argument(..., help="One or more page addresses."),
    fmt: str = typer.Option("text", "--format", "-f", help="text or markdown."),
    as_json: bool = JSON_OPT,
) -> None:
    """Fetch pages and print their clean article text."""
    if fmt not in ("text", "markdown"):
        _fail(f"unknown format {fmt!r}, use text or markdown", as_json)
    from .extract import read_pages

    docs, failed = read_pages(urls, fmt)
    failed = [{"url": f.get("url"), "error": f.get("error")} for f in failed]
    if as_json:
        _emit({"results": docs, "failed": failed})
    else:
        for doc in docs:
            typer.secho(doc.get("title") or doc.get("url", ""), bold=True)
            typer.echo(doc.get("url", ""))
            typer.echo(f"\n{doc.get('content', '')}\n")
        for f in failed:
            typer.secho(f"failed: {f['url']} ({f['error']})", fg=typer.colors.RED, err=True)
    if failed and not docs:
        raise typer.Exit(1)


def main() -> None:  # extraction uses worker processes, so entry points need a real main
    app()


if __name__ == "__main__":
    main()
# Stand: 24.10.2026
