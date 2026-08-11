"""Competitor AI / transformation moves agent."""

from __future__ import annotations

import json
from typing import Any

from app.tools.llm import llm_json
from app.tools.search import search_web


SYSTEM = """You identify competitors and their AI or transformation moves.
Return ONLY valid JSON:
{
  "subject": "",
  "competitors": [
    {
      "name": "",
      "why": "",
      "ai_or_transformation_moves": [],
      "strengths": [],
      "weaknesses": []
    }
  ],
  "comparison_summary": "",
  "sources": [{"title": "", "url": ""}]
}
List 4-6 competitors when possible. Be specific about AI or automation moves.
"""


def research_competitors(
    query: str,
    subject: str | None = None,
    company_data: dict[str, Any] | None = None,
    industry_data: dict[str, Any] | None = None,
    news_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    focus = (subject or query).strip()
    results = search_web(
        f"{focus} competitors AI automation digital transformation",
        max_results=6,
    )
    context = {
        "company": _slim(company_data),
        "industry": _slim(industry_data),
        "news": _slim(news_data),
        "search_results": results,
    }

    try:
        data = llm_json(
            SYSTEM,
            f"Research query: {query}\nSubject: {focus}\n\nContext:\n{json.dumps(context, indent=2, default=str)}",
            temperature=0.3,
        )
        if isinstance(data, dict):
            if not data.get("sources"):
                data["sources"] = [
                    {"title": r["title"], "url": r["url"]} for r in results if r.get("url")
                ]
            return data
    except Exception as exc:
        return {
            "subject": focus,
            "competitors": [],
            "comparison_summary": f"Competitor analysis failed: {exc}",
            "sources": [{"title": r["title"], "url": r["url"]} for r in results if r.get("url")],
        }

    return {"subject": focus, "competitors": [], "sources": []}


def _slim(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    skip = {"raw_results", "raw_articles"}
    return {k: v for k, v in data.items() if k not in skip}
