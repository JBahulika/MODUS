"""Synthesizer — merge agent outputs into a transformation brief."""

from __future__ import annotations

import json
from typing import Any

from app.tools.llm import llm_json


SYSTEM = """You are an enterprise AI transformation research analyst.
Merge the agent outputs into one decision-ready brief.
Every recommendation must include a rationale and supporting findings.
If evidence is thin, lower confidence and say what is missing.
Return ONLY valid JSON:
{
  "query": "",
  "subject": "",
  "executive_summary": "",
  "context": {
    "industry": null,
    "company_or_subject_summary": "",
    "operating_notes": ""
  },
  "industry_signals": {
    "trends": [],
    "ai_adoption_patterns": [],
    "pressures": []
  },
  "recent_news": [{"headline": "", "summary": "", "url": "", "date": ""}],
  "competitors": [{"name": "", "why": "", "ai_or_transformation_moves": []}],
  "ai_opportunities": [
    {
      "title": "",
      "process_or_function": "",
      "why_now": "",
      "expected_impact": "",
      "complexity": "low|medium|high"
    }
  ],
  "risks": [
    {
      "title": "",
      "category": "",
      "severity": "low|medium|high",
      "detail": "",
      "mitigation": ""
    }
  ],
  "recommendations": [
    {
      "title": "",
      "priority": "high|medium|low",
      "rationale": "",
      "supporting_findings": [],
      "sources": [{"title": "", "url": ""}],
      "confidence": "high|medium|low"
    }
  ],
  "conflicts": [],
  "confidence_notes": [],
  "sources": [{"title": "", "url": ""}]
}
"""


def synthesize_report(
    query: str,
    plan: dict[str, Any],
    company: dict[str, Any],
    industry: dict[str, Any],
    news: dict[str, Any],
    competitors: dict[str, Any],
    opportunities: dict[str, Any],
    risks: dict[str, Any],
) -> dict[str, Any]:
    subject = (
        plan.get("subject")
        or company.get("subject")
        or query
    )
    bundle = {
        "plan": plan,
        "company": _slim(company),
        "industry": _slim(industry),
        "news": _slim(news),
        "competitors": _slim(competitors),
        "opportunities": _slim(opportunities),
        "risks": _slim(risks),
    }

    try:
        data = llm_json(
            SYSTEM,
            f"Query: {query}\nSubject: {subject}\n\nAgent outputs:\n{json.dumps(bundle, indent=2, default=str)}",
            temperature=0.25,
        )
        if isinstance(data, dict):
            data["query"] = data.get("query") or query
            data["subject"] = data.get("subject") or subject
            data["sources"] = _merge_sources(
                data.get("sources") or [],
                company,
                industry,
                news,
                competitors,
                opportunities,
                risks,
            )
            data["recommendations"] = _normalize_recommendations(
                data.get("recommendations") or []
            )
            data["agent_raw"] = bundle
            return data
    except Exception as exc:
        return _fallback(query, subject, company, industry, news, competitors, opportunities, risks, str(exc))

    return _fallback(query, subject, company, industry, news, competitors, opportunities, risks, "empty synthesizer")


def _normalize_recommendations(items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "title": item.get("title") or "Recommendation",
                "priority": item.get("priority") or "medium",
                "rationale": item.get("rationale") or "",
                "supporting_findings": item.get("supporting_findings") or [],
                "sources": item.get("sources") or [],
                "confidence": item.get("confidence") or "medium",
            }
        )
    return out


def _slim(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    skip = {"raw_results", "raw_articles"}
    return {k: v for k, v in data.items() if k not in skip}


def _merge_sources(*parts: Any) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for part in parts:
        if isinstance(part, list):
            items = part
        elif isinstance(part, dict):
            items = part.get("sources") or []
        else:
            items = []
        for src in items:
            if not isinstance(src, dict):
                continue
            url = src.get("url") or ""
            if url and url not in seen:
                seen.add(url)
                out.append({"title": src.get("title") or url, "url": url})
    return out[:40]


def _fallback(
    query: str,
    subject: str,
    company: dict[str, Any],
    industry: dict[str, Any],
    news: dict[str, Any],
    competitors: dict[str, Any],
    opportunities: dict[str, Any],
    risks: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    opps = opportunities.get("opportunities") or []
    recommendations = []
    for opp in opps[:3]:
        if not isinstance(opp, dict):
            continue
        recommendations.append(
            {
                "title": opp.get("title") or "Explore AI opportunity",
                "priority": "medium",
                "rationale": opp.get("why_now") or opp.get("expected_impact") or "",
                "supporting_findings": [opp.get("evidence") or opp.get("process_or_function") or ""],
                "sources": opportunities.get("sources") or [],
                "confidence": "low",
            }
        )

    return {
        "query": query,
        "subject": subject,
        "executive_summary": company.get("summary")
        or f"Brief assembled with incomplete synthesis ({error}).",
        "context": {
            "industry": company.get("industry") or industry.get("industry"),
            "company_or_subject_summary": company.get("summary") or "",
            "operating_notes": company.get("operating_model_notes") or "",
        },
        "industry_signals": {
            "trends": industry.get("trends") or [],
            "ai_adoption_patterns": industry.get("ai_adoption_patterns") or [],
            "pressures": industry.get("regulatory_or_market_pressures") or [],
        },
        "recent_news": [
            {
                "headline": h.get("headline"),
                "summary": h.get("summary"),
                "url": h.get("url"),
                "date": h.get("date"),
            }
            for h in (news.get("highlights") or [])
        ],
        "competitors": competitors.get("competitors") or [],
        "ai_opportunities": opps,
        "risks": risks.get("risks") or [],
        "recommendations": recommendations,
        "conflicts": risks.get("conflicts") or [],
        "confidence_notes": (risks.get("confidence_notes") or []) + [error],
        "sources": _merge_sources(company, industry, news, competitors, opportunities, risks),
        "agent_raw": {
            "company": _slim(company),
            "industry": _slim(industry),
            "news": _slim(news),
            "competitors": _slim(competitors),
            "opportunities": _slim(opportunities),
            "risks": _slim(risks),
        },
    }
