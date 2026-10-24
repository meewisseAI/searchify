# Architecture

## Search backend chain

`search(query)` tries the configured `SEARCH_BACKEND`, then `SEARCH_FALLBACK`,
and returns the first backend that yields results.

- **duckduckgo** — keyless, via the `ddgs` package. The convenient baseline.
- **searxng** — your own SearXNG instance (`SEARXNG_URL`). Keyless, fast, private.
  Needs JSON output enabled in the instance (`settings.yml`: `search.formats`
  includes `json`).
- **serper** — optional Google results via Serper. Runs only if `SERPER_API_KEY`
  is set, as a last resort.

Each backend returns a uniform list of `{title, url, content, engine}` hits,
deduplicated and domain-filtered.

## Extraction load ladder

Described with its limits and settings in the [README](../README.md#http-service).
The outbound proxy only ever connects to public addresses on ports 80/443/8080/8443.

## Reranking

`rerank(query, items)` scores each candidate with a cross-encoder and reorders
best-first. The default is a public MiniLM, downloaded on first use. Set
`RERANKER_MODEL` to another Hugging Face name or a local directory to use your own.
<!-- Stand: 24.10.2026 -->
