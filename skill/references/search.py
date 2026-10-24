#!/usr/bin/env python3
"""Multi-engine web search with a graceful fallback chain.

One query, several search engines: Tavily, Exa, Serper (Google SERP) and Jina.
Each engine is used only if its API key is set; a missing key, a connection
error, 401/429 or an empty result moves on to the next engine. Results from
several engines are merged by URL, and hits found by more than one engine rank
higher.

Keys are read from the environment, then from a .env file next to this script
(KEY=value per line). Set only the engines you have:

  TAVILY_API_KEY   tavily.com      (free tier)
  EXA_API_KEY      exa.ai          (free tier)
  SERPER_API_KEY   serper.dev      (free Google SERP quota)
  JINA_API_KEY     jina.ai         (free tier)

Usage:
  search.py "your query" ["second query" ...]
  --since 30d|2026-09-01   only newer pages (Tavily/Serper/Exa real; others best effort)
  --site domain            restrict to a domain (repeatable, also filtered locally)
  --exclude domain         drop a domain (repeatable)
  --lang de                language hint
  --news                   news instead of general web (Tavily, Serper)
  --n 20                   results per query (default 10)
  --engine NAME            use only one: tavily, exa-api, serper, jina
  --fan                    query every keyed engine in parallel and merge
  --seen path/seen.txt     shared found-list for a wave of agents (marks [new]/[known])
  --social [all|reddit,x,instagram,tiktok]  run each query per platform, limited to its domains
  --json                   machine-readable output
  --status                 show which engines have a key
"""
import argparse
import copy
import fcntl
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

TIMEOUT = 20

CHAIN = ["tavily", "exa-api", "serper", "jina"]
PAID = {"tavily": "TAVILY_API_KEY", "exa-api": "EXA_API_KEY",
        "serper": "SERPER_API_KEY", "jina": "JINA_API_KEY"}
KEYS = list(PAID.values())


class EngineDown(Exception):
    pass


def load_keys():
    keys = {k: os.environ[k] for k in KEYS if os.environ.get(k)}
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env):
        with open(env, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k in KEYS and v and k not in keys:
                        keys[k] = v
    return keys


def since_date(s):
    if not s:
        return None
    s = s.strip()
    if re.fullmatch(r"\d+d", s):
        return date.today() - timedelta(days=int(s[:-1]))
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise SystemExit(f"--since: use 30d or 2026-09-01, not {s!r}")


def http_json(url, body=None, headers=None, timeout=TIMEOUT):
    data = json.dumps(body).encode() if body is not None else None
    hdr = {"Content-Type": "application/json", "Accept": "application/json"}
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdr,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise EngineDown(f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise EngineDown(type(e).__name__)


def hit(title, url, snippet, published, engine):
    return {"title": (title or "").strip(), "url": (url or "").strip(),
            "snippet": (snippet or "").strip(), "published": (published or "").strip(),
            "engine": engine}


def time_range(since_d):
    if not since_d:
        return None
    days = (date.today() - since_d).days
    if days <= 1:
        return "day"
    if days <= 7:
        return "week"
    if days <= 31:
        return "month"
    return "year"


def _missing(name):
    raise EngineDown(f"no {name}")


def s_tavily(q, o, keys):
    key = keys.get("TAVILY_API_KEY") or _missing("TAVILY_API_KEY")
    body = {"api_key": key, "query": q, "max_results": min(o.n, 20),
            "topic": "news" if o.news else "general",
            "include_domains": o.site, "exclude_domains": o.exclude}
    rng = time_range(o.since_d)
    if rng:
        body["time_range"] = rng
    r = http_json("https://api.tavily.com/search", body)
    return [hit(x.get("title"), x.get("url"), x.get("content"),
                x.get("published_date"), "tavily") for x in r.get("results", [])]


def s_exa_api(q, o, keys):
    key = keys.get("EXA_API_KEY") or _missing("EXA_API_KEY")
    body = {"query": q, "numResults": min(o.n, 25), "type": "auto",
            "contents": {"summary": True}}
    if o.site:
        body["includeDomains"] = o.site
    if o.exclude:
        body["excludeDomains"] = o.exclude
    if o.since_d:
        body["startPublishedDate"] = o.since_d.isoformat() + "T00:00:00.000Z"
    r = http_json("https://api.exa.ai/search", body, {"x-api-key": key})
    return [hit(x.get("title"), x.get("url"), x.get("summary"),
                x.get("publishedDate"), "exa-api") for x in r.get("results", [])]


def s_serper(q, o, keys):
    key = keys.get("SERPER_API_KEY") or _missing("SERPER_API_KEY")
    qq = q + "".join(f" site:{d}" for d in o.site[:1])
    body = {"q": qq, "num": min(o.n, 20)}
    if o.lang:
        body["hl"] = o.lang
    rng = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}.get(time_range(o.since_d))
    if rng:
        body["tbs"] = rng
    url = "https://google.serper.dev/" + ("news" if o.news else "search")
    r = http_json(url, body, {"X-API-KEY": key})
    rows = r.get("news") if o.news else r.get("organic")
    return [hit(x.get("title"), x.get("link"), x.get("snippet"),
                x.get("date", ""), "serper") for x in (rows or [])]


def s_jina(q, o, keys):
    key = keys.get("JINA_API_KEY") or _missing("JINA_API_KEY")
    qq = q + "".join(f" site:{d}" for d in o.site[:1])
    headers = {"Authorization": f"Bearer {key}", "X-Respond-With": "no-content"}
    if len(o.site) > 1:
        headers.pop("X-Respond-With")
    r = http_json("https://s.jina.ai/?q=" + urllib.parse.quote(qq), None, headers)
    return [hit(x.get("title"), x.get("url"), x.get("description"),
                x.get("date"), "jina") for x in (r.get("data") or [])][:o.n]


ENGINES = {"tavily": s_tavily, "exa-api": s_exa_api, "serper": s_serper, "jina": s_jina}


# ---- flow ----

def norm_url(u):
    p = urllib.parse.urlsplit(u.strip())
    query = "&".join(kv for kv in p.query.split("&")
                     if kv and not kv.startswith(("utm_", "ref=", "fbclid", "gclid")))
    host = p.netloc.lower().removeprefix("www.")
    return urllib.parse.urlunsplit(("https", host, p.path.rstrip("/"), query, ""))


def _has_key(name, keys):
    return PAID[name] in keys


def run_query(q, o, keys, log):
    names = [o.engine] if o.engine else CHAIN
    if o.fan and not o.engine:
        usable = [n for n in names if _has_key(n, keys)]

        def one(name):
            try:
                return ENGINES[name](q, o, keys)
            except EngineDown as e:
                log.append(f"{name}: {e}")
                return []
        if not usable:
            log.append("no engine has a key")
            return []
        with ThreadPoolExecutor(len(usable)) as ex:
            return [h for part in ex.map(one, usable) for h in part]
    for name in names:
        if not o.engine and not _has_key(name, keys):
            log.append(f"{name}: no {PAID[name]}")
            continue
        try:
            hits = ENGINES[name](q, o, keys)
            if hits:
                return hits
            log.append(f"{name}: 0 results")
        except EngineDown as e:
            log.append(f"{name}: {e}")
    return []


SOCIAL = {"reddit": ["reddit.com"], "x": ["x.com", "twitter.com"],
          "instagram": ["instagram.com"], "tiktok": ["tiktok.com"]}


def social_platforms(arg):
    names = list(SOCIAL) if arg == "all" else [n.strip() for n in arg.split(",") if n.strip()]
    unknown = [n for n in names if n not in SOCIAL]
    if unknown:
        raise SystemExit(f"--social knows only {','.join(SOCIAL)}, not {','.join(unknown)}")
    return names


def _terms(q):
    return [t for t in re.findall(r"\w+", q.lower()) if len(t) >= 4 and not t.isdigit()]


def social_relevant(h, q):
    # Restricted to one domain, engines with no hit return random, sometimes NSFW,
    # pages. Keep only what contains a query term and is not just the platform root.
    text = f"{h.get('title', '')} {h.get('snippet', '')} {h['url']}".lower()
    if "nsfw" in text or urllib.parse.urlsplit(h["url"]).path.strip("/") == "":
        return False
    terms = _terms(q)
    return not terms or any(t in text for t in terms)


def run_social(queries, o, keys, log):
    def one(job):
        name, q = job
        po = copy.copy(o)
        po.site = SOCIAL[name]
        plog = []
        hits = [dict(h, platform=name) for h in run_query(q, po, keys, plog)
                if h.get("url") and host_ok(h, po) and social_relevant(h, q)]
        log.extend(f"{name}: {m}" for m in plog)
        return hits
    jobs = [(n, q) for n in social_platforms(o.social) for q in queries]
    with ThreadPoolExecutor(min(8, len(jobs))) as ex:
        return [h for part in ex.map(one, jobs) for h in part]


def host_ok(h, o):
    host = urllib.parse.urlsplit(h["url"]).netloc.lower().removeprefix("www.")
    match = lambda d: host == d or host.endswith("." + d)
    if o.site and not any(match(d) for d in o.site):
        return False
    return not any(match(d) for d in o.exclude)


def merge(hits):
    out = {}
    for h in hits:
        k = norm_url(h["url"])
        if k in out:
            prev = out[k]
            if h["engine"] not in prev["engine"].split("+"):
                prev["engine"] += "+" + h["engine"]  # found by several = stronger
            prev["snippet"] = prev["snippet"] or h["snippet"]
            prev["published"] = prev["published"] or h["published"]
        else:
            out[k] = dict(h, key=k)
    return sorted(out.values(), key=lambda h: -h["engine"].count("+"))


def mark_seen(hits, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        known = {line.split("\t", 1)[0] for line in f if line.strip()}
        stamp = time.strftime("%Y-%m-%d %H:%M")
        for h in hits:
            h["new"] = h["key"] not in known
            if h["new"]:
                f.write(f"{h['key']}\t{h['title'][:80]}\t{stamp}\n")
                known.add(h["key"])
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)


def status(keys):
    for name in CHAIN:
        print(f"{name:8} " + ("key set" if _has_key(name, keys) else f"no {PAID[name]}"))


def search(queries, *, n=10, since=None, site=None, exclude=None, lang=None,
           news=False, engine=None, fan=False, social=None, keys=None):
    """Library entry point. Returns a list of merged hit dicts."""
    o = argparse.Namespace(queries=list(queries), n=n, since=since, site=list(site or []),
                           exclude=list(exclude or []), lang=lang, news=news, engine=engine,
                           fan=fan, social=social)
    o.since_d = since_date(since)
    keys = keys if keys is not None else load_keys()
    log = []
    if social:
        hits = merge(run_social(o.queries, o, keys, log))
        order = list(SOCIAL)
        hits.sort(key=lambda h: order.index(h["platform"]))
    else:
        hits = []
        for q in o.queries:
            hits += run_query(q, o, keys, log)
        hits = merge([h for h in hits if h.get("url") and host_ok(h, o)])
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="*")
    ap.add_argument("--since")
    ap.add_argument("--site", action="append", default=[])
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--lang")
    ap.add_argument("--news", action="store_true")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--engine", choices=list(ENGINES))
    ap.add_argument("--fan", action="store_true")
    ap.add_argument("--seen")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--social", nargs="?", const="all")
    o = ap.parse_args()
    keys = load_keys()
    if o.status:
        return status(keys)
    if not o.queries:
        ap.error("at least one query")
    o.since_d = since_date(o.since)

    log, hits = [], []
    if o.social:
        hits = merge(run_social(o.queries, o, keys, log))
        order = list(SOCIAL)
        hits.sort(key=lambda h: order.index(h["platform"]))
    else:
        for q in o.queries:
            hits += run_query(q, o, keys, log)
        hits = merge([h for h in hits if h.get("url") and host_ok(h, o)])
    log = list(dict.fromkeys(log))
    if o.seen:
        mark_seen(hits, o.seen)

    if o.json:
        print(json.dumps({"hits": hits, "log": log}, ensure_ascii=False, indent=1))
    else:
        for i, h in enumerate(hits, 1):
            tag = "" if "new" not in h else ("[new] " if h["new"] else "[known] ")
            date_s = f" ({h['published']})" if h["published"] else ""
            plat = f"[{h['platform']}] " if "platform" in h else ""
            print(f"{i}. {plat}{tag}{h['title']}{date_s} | {h['engine']}\n   {h['url']}")
            if h["snippet"]:
                print(f"   {h['snippet'][:220]}")
        if log:
            print("\n# skipped: " + "; ".join(log), file=sys.stderr)
    if not hits:
        sys.exit(1)


if __name__ == "__main__":
    main()
# Stand: 24.10.2026
