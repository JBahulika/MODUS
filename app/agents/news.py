"""News agent — recent transformation and AI-related headlines."""

from __future__ import annotations

import json
from typing import Any

from app.tools.llm import llm_json
from app.tools.news import search_news
from app.tools.search import search_web


SYSTEM = """You summarize recent news relevant to enterprise AI transformation.
Return ONLY valid JSON:
{
  "subject": "",
  "highlights": [
    {
      "headline": "",
      "category": "ai|automation|partnership|regulation|restructuring|funding|other",
      "summary": "",
      "url": "",
      "date": ""
    }
  ],
  "summary": "",
  "sources": [{"title": "", "url": ""}]
}
Prefer the last ~30 days. Skip duplicates. Max 8 highlights.
"""


def research_news(query: str, subject: str | None = None) -> dict[str, Any]:
    focus = (subject or query).strip()
    articles = search_news(focus, days=30, max_results=8)
    extra = search_web(f"{focus} AI automation news", max_results=4)
    for item in extra:
        articles.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "published_at": "",
                "source": item.get("source", "search"),
            }
        )

    try:
        data = llm_json(
            SYSTEM,
            f"Research query: {query}\nSubject: {focus}\n\nArticles:\n{json.dumps(articles, indent=2)}",
        )
        if isinstance(data, dict):
            if not data.get("sources"):
                data["sources"] = [
                    {"title": a["title"], "url": a["url"]} for a in articles if a.get("url")
                ]
            data["raw_articles"] = articles
            return data
    except Exception as exc:
        return {
            "subject": focus,
            "highlights": [
                {
                    "headline": a.get("title", ""),
                    "category": "other",
                    "summary": a.get("snippet", ""),
                    "url": a.get("url", ""),
                    "date": a.get("published_at", ""),
                }
                for a in articles[:6]
            ],
            "summary": f"Raw headlines only (summarizer error: {exc})",
            "sources": [{"title": a["title"], "url": a["url"]} for a in articles if a.get("url")],
            "raw_articles": articles,
        }

    return {"subject": focus, "highlights": [], "sources": [], "raw_articles": articles}
