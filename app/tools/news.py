"""News lookup via NewsAPI with search fallback."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import get_settings
from app.tools.search import search_web


def search_news(company: str, days: int = 30, max_results: int = 8) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.news_api_key:
        try:
            articles = _news_api(company, days, max_results, settings.news_api_key)
            if articles:
                return articles
        except Exception:
            pass
    return _news_via_search(company, max_results)


def _news_api(
    company: str, days: int, max_results: int, api_key: str
) -> list[dict[str, Any]]:
    from newsapi import NewsApiClient

    client = NewsApiClient(api_key=api_key)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    response = client.get_everything(
        q=company,
        from_param=since,
        language="en",
        sort_by="publishedAt",
        page_size=max_results,
    )
    articles = []
    for item in response.get("articles", [])[:max_results]:
        articles.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "snippet": item.get("description") or item.get("content") or "",
                "published_at": item.get("publishedAt") or "",
                "source": (item.get("source") or {}).get("name") or "newsapi",
            }
        )
    return articles


def _news_via_search(company: str, max_results: int) -> list[dict[str, Any]]:
    results = search_web(f"{company} latest news last 30 days", max_results=max_results)
    return [
        {
            "title": r["title"],
            "url": r["url"],
            "snippet": r["snippet"],
            "published_at": "",
            "source": r.get("source", "search"),
        }
        for r in results
    ]
