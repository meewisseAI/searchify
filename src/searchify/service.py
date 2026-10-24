"""Optional HTTP service exposing search and extraction.

    uvicorn searchify.service:app

Needs the optional extra: ``pip install "searchify[api]"``.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .extract import extract as extract_urls
from .search import SearchBackendError, search as web_search

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
    filters = req.model_dump(exclude={"query", "max_results", "backend"}, exclude_none=True)
    try:
        hits = web_search(req.query, req.max_results, backend=req.backend, **filters)
    except SearchBackendError as exc:
        return {"error": str(exc), "results": []}
    return {"results": hits}


@app.post("/extract")
def extract_endpoint(req: ExtractRequest) -> dict:
    return {"results": extract_urls(req.urls, fmt=req.fmt)}
# Stand: 24.10.2026
