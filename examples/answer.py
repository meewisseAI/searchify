"""Answer a question with the passages that say it, straight from the web.

    python examples/answer.py "How much does the NVIDIA DGX Spark cost and how much memory does it have?"
"""
import sys
import time
from urllib.parse import urlparse

from searchify import extract, rerank, search


def short(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " ..."


def main() -> None:
    question = " ".join(sys.argv[1:]) or "How much does the NVIDIA DGX Spark cost and how much memory does it have?"

    t = time.perf_counter()
    hits = search(question, max_results=8)
    pages = extract([h["url"] for h in hits[:5]])
    read_s = time.perf_counter() - t

    passages = [
        {"content": para.strip(), "url": page["url"]}
        for page in pages
        for para in page["content"].split("\n")
        if len(para.split()) >= 12
    ]
    rerank(question, passages[:1])  # load the model once, so the timing below is the ranking
    t = time.perf_counter()
    ranked = rerank(question, passages)
    rank_s = time.perf_counter() - t

    best, sites = [], set()  # the best passage per site, so every line adds a source
    for p in ranked:
        site = urlparse(p["url"]).netloc
        if site not in sites:
            sites.add(site)
            best.append(p)
        if len(best) == 3:
            break

    if not best:
        print("No pages found. DuckDuckGo may be rate-limiting you; try again in a minute or set SEARXNG_URL.")
        return
    for i, p in enumerate(best, 1):
        print(f"{i}. {short(p['content'])}\n   {urlparse(p['url']).netloc}")
    print(f"\nsearched and read {len(pages)} pages in {read_s:.1f} s, "
          f"ranked {len(passages)} passages in {rank_s:.1f} s")


if __name__ == "__main__":  # extraction uses worker processes, so the guard is required
    main()
# Stand: 24.10.2026
