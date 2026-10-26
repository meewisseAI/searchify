"""Optional HTTP service exposing search and extraction.

    uvicorn searchify.service:app

Needs the optional extra: ``pip install "searchify[api]"``.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .extract import read_pages
from .search import search_report

app = FastAPI(title="searchify", description="Local-first web search and clean extraction")


class SearchRequest(BaseModel):
    query: str
    max_results: int = Field(10, ge=1, le=50)
    backend: Optional[str] = None
    language: Optional[str] = None
    time_range: Optional[str] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None


class ExtractRequest(BaseModel):
    urls: List[str]
    fmt: str = "text"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search")
def search_endpoint(req: SearchRequest) -> dict:
    """Hits, plus ``error`` (the last backend error, or null) and ``backend`` (the
    one that answered), so an empty list can be told from a rate limit."""
    filters = req.model_dump(exclude={"query", "max_results", "backend"}, exclude_none=True)
    report = search_report(req.query, req.max_results, backend=req.backend, **filters)
    return {"results": report["results"], "error": report["error"], "backend": report["backend"]}


@app.post("/extract")
def extract_endpoint(req: ExtractRequest) -> dict:
    """Clean pages under ``results`` (each with ``stage``: static, browser,
    browser-direct, stealth or tavily) and the rest under ``failed`` with a reason."""
    docs, failed = read_pages(req.urls, req.fmt)
    return {"results": docs, "failed": [{"url": f.get("url"), "error": f.get("error")} for f in failed]}
# Stand: 24.10.2026
