# Channels, tools, search technique

Perishable details (prices, rate limits, endpoints) live only here, not in
SKILL.md. Verify against the provider's page before relying on them.

## First grab: search.py

`python3 references/search.py "query" ...`
- Queries Tavily, Exa, Serper and Jina. Each engine runs only if its key is set;
  a missing key, a connection error, 401/429 or an empty result moves on.
- `--fan` queries every keyed engine in parallel and merges by URL. Hits found by
  several engines rank higher. Good for market scans and "find everything".
- Filters: `--since 30d|2026-09-01`, `--site domain` / `--exclude domain`
  (repeatable, also filtered locally), `--lang de`, `--news`, `--n 20`,
  `--engine exa-api`.
- `--seen path/seen.txt`: a shared found-list for a wave of agents (see below).
- `--social [all|reddit,x,instagram,tiktok]`: run each query per platform,
  limited to its domains.
- `--status` shows which engines have a key.
- Keys: environment, then a `.env` next to the script.

## Search technique toolbox

Take what fits the question. More hits almost always come from more different
queries, not from more results per query.
- **Languages**: every question in at least the local language and English; for
  EU topics also FR/ES or the country's language. Look up the domain term per
  country instead of translating literally.
- **Synonyms and perspectives**: provider side ("call for applications",
  "tender") and participant side ("I attended", "experience report"). Add a broad
  term and a niche term.
- **Operators** (real on Serper/Jina/Google in a browser, else via `--site`):
  `site:` for domains and TLDs, `filetype:pdf` for calls and guidelines,
  `intitle:`, `"exact phrase"`, `-word`, `OR`. For Exa, describe the ideal page
  in full sentences rather than keywords.
- **Time**: `--since` for anything with a deadline, price or status. Put the year
  in the query, since undated pages otherwise return old rounds.
- **Snowball**: squeeze good hits. Read aggregators and "awesome" lists fully,
  follow links to partners/funders/jury, use Exa `category:company`/`category:people`
  for similar, GitHub stars/forks, citations (OpenAlex).
- **Saturation as a stop**: fan out until two or three new query rounds barely add
  anything new. Only then go deep.

## Finding niches (programs, invitations, calls)

The good things rarely sit on the front page; they live in forms, mailing lists
and groups. Searching publicly linked material is fine; guessing or brute-forcing
non-public invite links is not (and does not work, the IDs are random).
- **Public forms**: `--site docs.google.com --site forms.gle --site typeform.com
  --site tally.so --site airtable.com --site lu.ma --site eventbrite.com` plus
  topic, "application", year. No `--since` here: forms have no date.
- **Mailing lists and groups**: public Telegram channels (preview at
  t.me/s/<channel>, readable without login), Discord directories, mailing-list
  archives (groups.google.com), Substack/newsletter archives, LinkedIn posts with
  "applications open" / "we are looking for".
- **Who is already in**: find last year's participant posts ("I attended",
  "delegate", "fellow"); their profiles show the next programs.
- **Institutions** (UN, parliaments, EU): youth-delegate, trainee and youth-forum
  pages, plus the lists they announce through (SALTO, youth.europa.eu, UN Youth Envoy).

## Finding people (for outreach)

Only public, professional material: posts, talks, repos, company pages. Do not
guess private addresses, no leaks, nothing behind a login.
- **Role to person**: Exa `category:people <role> <company> <city>`, Tavily
  `--site linkedin.com "<company>" "<role>"`.
- **Person to traces**: name in quotes plus company via `--fan`: LinkedIn posts,
  conference speaker lists, podcasts/YouTube, GitHub, blog posts. What the person
  posted last is the hook for the message.

## Agent waves

- All agents of a wave get the same path `seen.txt` and call search.py with
  `--seen`. Wave 2 sees what wave 1 already has and targets `[new]`. The file is
  file-locked, safe in parallel.
- At most 5 agents per wave; subagents never spawn subagents.

## Reading pages

For the clean main text of a page, and for JavaScript or bot-protected pages, use
the `searchify` engine package: `from searchify import extract`, or its HTTP
service (`POST /extract`). It starts with a fast fetch and opens a browser only
when a page needs it. After HTTP 200, check it is a real content page and not a
Cloudflare or consent interstitial.

## Specialist source APIs

- **EU Funding and Tenders Search API** (keyless, unofficial, verify the endpoint
  against ec.europa.eu): Erasmus+, Horizon, Creative Europe.
- **OffeneRegister.de**: German company register and officers.
- **HN Algolia** (hn.algolia.com/api), **Arctic Shift**
  (arctic-shift.photon-reddit.com/api): Hacker News and Reddit, keyless.
- **arXiv / Semantic Scholar / OpenAlex**: papers and the citation graph (see papers.py).
- **youth.europa.eu/solidarity** (search_en): open API via curl.

## Checking claims

Numbers, prices and anything a decision rests on: run them through
`references/sources.py` and check with `sources.py verify --numbers` before you
call it done.

## Notes on engines

- Without `EXA_API_KEY`, Exa effectively drops out. Query diversity matters more
  than ranking: a few normal plus a few niche queries (quotes, "call for
  applications", `site:`, deadline terms) beats more results per query.
<!-- Stand: 24.10.2026 -->
