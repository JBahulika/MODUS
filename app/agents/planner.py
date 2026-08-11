"""Planner agent — frames an enterprise transformation research plan."""

from __future__ import annotations

from typing import Any

from app.tools.llm import llm_json


SYSTEM = """You are a research planner for enterprise AI transformation intelligence.
Given a research query, produce a JSON plan.
Always assign all specialist agents for a full brief.
Return ONLY valid JSON:
{
  "query": "normalized query",
  "subject": "main company, industry, or function being researched",
  "industry_hint": "industry if known else null",
  "objectives": ["..."],
  "agents": ["company", "industry", "news", "competitors", "opportunity"],
  "notes": "short rationale"
}
"""


def plan_research(query: str) -> dict[str, Any]:
    try:
        result = llm_json(
            SYSTEM,
            f"Plan transformation research for: {query}",
            temperature=0.1,
        )
        if isinstance(result, dict):
            result.setdefault("query", query)
            result.setdefault(
                "agents",
                ["company", "industry", "news", "competitors", "opportunity"],
            )
            result.setdefault("subject", query.strip())
            return result
    except Exception:
        pass

    return {
        "query": query.strip(),
        "subject": query.strip(),
        "industry_hint": None,
        "objectives": [
            "Company and operating context",
            "Industry transformation signals",
            "Recent news and market moves",
            "Competitor AI moves",
            "AI opportunity areas",
            "Risks and recommendations",
        ],
        "agents": ["company", "industry", "news", "competitors", "opportunity"],
        "notes": "Full enterprise transformation research plan.",
    }
