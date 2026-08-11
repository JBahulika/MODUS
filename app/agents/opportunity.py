"""AI opportunity areas agent."""

from __future__ import annotations

import json
from typing import Any

from app.tools.llm import llm_json
from app.tools.search import search_web


SYSTEM = """You identify concrete AI opportunity areas for an enterprise transformation brief.
Return ONLY valid JSON:
{
  "subject": "",
  "opportunities": [
    {
      "title": "",
      "process_or_function": "",
      "why_now": "",
      "expected_impact": "",
      "complexity": "low|medium|high",
      "evidence": ""
    }
  ],
  "summary": "",
  "sources": [{"title": "", "url": ""}]
}
Prefer opportunities grounded in the search evidence. Max 6 opportunities.
If evidence is thin, say so in summary and keep complexity honest.
"""


def research_opportunities(
    query: str,
    subject: str | None = None,
    company_data: dict[str, Any] | None = None,
    industry_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    focus = (subject or query).strip()
    results = search_web(
        f"{focus} AI use cases automation opportunities enterprise",
        max_results=6,
    )
    extra = search_web(
        f"{focus} process automation ROI generative AI operations",
        max_results=4,
    )
    combined = results + extra
    context = {
        "company": _slim(company_data),
        "industry": _slim(industry_data),
        "search_results": combined,
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
                    {"title": r["title"], "url": r["url"]} for r in combined if r.get("url")
                ]
            data["raw_results"] = combined
            return data
    except Exception as exc:
        return {
            "subject": focus,
            "opportunities": [],
            "summary": f"Opportunity research incomplete: {exc}",
            "sources": [{"title": r["title"], "url": r["url"]} for r in combined if r.get("url")],
            "raw_results": combined,
        }

    return {"subject": focus, "opportunities": [], "sources": [], "raw_results": combined}


def _slim(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    skip = {"raw_results", "raw_articles"}
    return {k: v for k, v in data.items() if k not in skip}
