"""Web search with Tavily (preferred), DuckDuckGo, and Wikipedia fallbacks."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings


def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.tavily_api_key:
        try:
            hits = _tavily_search(query, max_results, settings.tavily_api_key)
            if hits:
                return hits
        except Exception:
            pass

    hits = _ddg_search(query, max_results)
    if hits:
        return hits

    # Last resort: Wikipedia summary for company-like queries
    company = _guess_company_term(query)
    if company:
        wiki = fetch_wikipedia(company)
        if wiki:
            return [wiki][:max_results]
    return []


def fetch_wikipedia(title: str) -> dict[str, Any] | None:
    """Fetch a Wikipedia page summary (no API key)."""
    slug = quote(title.strip().replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={"User-Agent": "ResearchAnalyst/1.0 (local research app)"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
        extract = data.get("extract") or ""
        page_url = (data.get("content_urls") or {}).get("desktop", {}).get("page") or data.get(
            "content_urls", {}
        ).get("page")
        if not page_url:
            page_url = f"https://en.wikipedia.org/wiki/{slug}"
        if not extract:
            return None
        return {
            "title": data.get("title") or title,
            "url": page_url,
            "snippet": extract,
            "source": "wikipedia",
        }
    except Exception:
        return None


def _tavily_search(query: str, max_results: int, api_key: str) -> list[dict[str, Any]]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    result = client.search(query=query, max_results=max_results, include_answer=False)
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "source": "tavily",
        }
        for item in result.get("results", [])
    ]


def _ddg_search(query: str, max_results: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    # Prefer the renamed package.
    try:
        from ddgs import DDGS  # type: ignore

        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(_normalize_ddg_item(item))
        if results:
            return results
    except Exception:
        results = []

    try:
        from duckduckgo_search import DDGS  # type: ignore

        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(_normalize_ddg_item(item))
    except Exception:
        return []
    return results


def _normalize_ddg_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item.get("title", ""),
        "url": item.get("href") or item.get("link") or item.get("url") or "",
        "snippet": item.get("body") or item.get("snippet") or item.get("description") or "",
        "source": "duckduckgo",
    }


def _guess_company_term(query: str) -> str | None:
    stop = {
        "company",
        "overview",
        "founders",
        "ceo",
        "headquarters",
        "products",
        "funding",
        "valuation",
        "revenue",
        "investors",
        "official",
        "website",
        "mission",
        "latest",
        "news",
        "competitors",
        "comparison",
        "alternatives",
        "hiring",
        "careers",
        "layoffs",
        "site:reddit.com",
        "review",
        "opinion",
        "experience",
        "customer",
        "complaints",
        "praise",
        "twitter",
        "linkedin",
        "or",
        "and",
        "the",
        "last",
        "days",
        "30",
    }
    tokens = [t for t in query.replace("|", " ").split() if t.lower() not in stop]
    if not tokens:
        return None
    # Keep first 1–3 meaningful tokens as a title guess.
    return " ".join(tokens[:3]).strip(" ,.")
