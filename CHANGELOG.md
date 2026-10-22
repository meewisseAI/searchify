# Changelog

## Unreleased

- Command line interface: `searchify search` and `searchify extract`, JSON by default, `--no-json` for readable text.

## 0.1.0

First release.

- Local-first web search: DuckDuckGo (keyless, default) and SearXNG (self-hosted).
- Optional cloud fallback: Google via Serper, off unless a key is set.
- Clean content extraction with a static-then-browser load ladder and an SSRF-safe proxy.
- Fast cross-encoder reranking with a swappable model.
- Small Python API and an optional HTTP service.
