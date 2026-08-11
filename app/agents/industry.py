"""Industry transformation signals agent."""

from __future__ import annotations

import json
from typing import Any

from app.tools.llm import llm_json
from app.tools.search import search_web


SYSTEM = """You research industry transformation and AI adoption signals.
Return ONLY valid JSON:
{
  "industry": "",
  "trends": [],
  "ai_adoption_patterns": [],
  "regulatory_or_market_pressures": [],
  "summary": "",
  "sources": [{"title": "", "url": ""}]
}
Be concrete. Prefer evidence from the search snippets over generic claims.
"""


def research_industry(
    query: str,
    subject: str | None = None,
    industry_hint: str | None = None,
) -> dict[str, Any]:
    focus = industry_hint or subject or query
    results = search_web(
        f"{focus} industry AI transformation trends automation",
        max_results=6,
    )
    extra = search_web(
        f"{focus} digital transformation challenges opportunities 2024 2025",
        max_results=4,
    )
    combined = _dedupe(results + extra)

    try:
        data = llm_json(
            SYSTEM,
            f"Research query: {query}\nFocus: {focus}\n\nSearch results:\n{json.dumps(combined, indent=2)}",
        )
        if isinstance(data, dict):
            if not data.get("sources"):
                data["sources"] = [
                    {"title": r["title"], "url": r["url"]} for r in combined if r.get("url")
                ]
            data["raw_results"] = combined
            return data
    except Exception as exc:
        return {
            "industry": str(focus),
            "trends": [],
            "ai_adoption_patterns": [],
            "regulatory_or_market_pressures": [],
            "summary": f"Industry research incomplete: {exc}",
            "sources": [{"title": r["title"], "url": r["url"]} for r in combined if r.get("url")],
            "raw_results": combined,
        }

    return {
        "industry": str(focus),
        "trends": [],
        "summary": "",
        "sources": [],
        "raw_results": combined,
    }


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        url = item.get("url") or ""
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        out.append(item)
    return out
