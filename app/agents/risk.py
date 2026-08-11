"""Risk and governance check agent."""

from __future__ import annotations

import json
from typing import Any

from app.tools.llm import llm_json
from app.tools.search import search_web


SYSTEM = """You assess risks and governance concerns for an enterprise AI transformation brief.
Use the provided agent findings and search results.
Return ONLY valid JSON:
{
  "subject": "",
  "risks": [
    {
      "title": "",
      "category": "data|model|process|people|compliance|vendor|security|other",
      "severity": "low|medium|high",
      "detail": "",
      "mitigation": ""
    }
  ],
  "governance_notes": [],
  "confidence_notes": [],
  "conflicts": [],
  "summary": "",
  "sources": [{"title": "", "url": ""}]
}
If evidence is thin or conflicting, say so in confidence_notes and conflicts.
Do not invent regulatory claims without support.
"""


def research_risks(
    query: str,
    subject: str | None = None,
    company_data: dict[str, Any] | None = None,
    industry_data: dict[str, Any] | None = None,
    news_data: dict[str, Any] | None = None,
    competitor_data: dict[str, Any] | None = None,
    opportunity_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    focus = (subject or query).strip()
    results = search_web(
        f"{focus} AI risks governance compliance challenges",
        max_results=5,
    )
    context = {
        "company": _slim(company_data),
        "industry": _slim(industry_data),
        "news": _slim(news_data),
        "competitors": _slim(competitor_data),
        "opportunities": _slim(opportunity_data),
        "search_results": results,
    }

    try:
        data = llm_json(
            SYSTEM,
            f"Research query: {query}\nSubject: {focus}\n\nContext:\n{json.dumps(context, indent=2, default=str)}",
            temperature=0.2,
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
            "risks": [],
            "governance_notes": [],
            "confidence_notes": [f"Risk analysis incomplete: {exc}"],
            "conflicts": [],
            "summary": f"Risk analysis incomplete: {exc}",
            "sources": [{"title": r["title"], "url": r["url"]} for r in results if r.get("url")],
        }

    return {"subject": focus, "risks": [], "sources": []}


def _slim(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    skip = {"raw_results", "raw_articles"}
    return {k: v for k, v in data.items() if k not in skip}
