"""Company / subject context agent."""

from __future__ import annotations

import json
from typing import Any

from app.tools.llm import llm_json
from app.tools.search import fetch_wikipedia, search_web


SYSTEM = """You extract structured company or subject context for enterprise AI research.
Return ONLY valid JSON:
{
  "subject": "",
  "founded": null,
  "ceo": null,
  "hq": null,
  "employees": null,
  "website": null,
  "industry": null,
  "products_or_services": [],
  "operating_model_notes": "",
  "summary": "",
  "sources": [{"title": "", "url": ""}]
}
Prefer facts supported by the snippets. Fill summary with 2-4 sentences when possible.
"""


def research_company(query: str, subject: str | None = None) -> dict[str, Any]:
    focus = (subject or query).strip()
    results = search_web(
        f"{focus} company overview operations products industry",
        max_results=6,
    )
    extra = search_web(f"{focus} digital transformation AI strategy", max_results=3)
    wiki = fetch_wikipedia(focus.split()[0:3] and " ".join(focus.split()[:3]) or focus)

    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in ([wiki] if wiki else []) + results + extra:
        if not item:
            continue
        url = item.get("url") or ""
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        combined.append(item)

    if not combined:
        return {
            "subject": focus,
            "summary": "No public overview sources were available.",
            "sources": [],
            "raw_results": [],
        }

    try:
        data = llm_json(
            SYSTEM,
            f"Research query: {query}\nSubject: {focus}\n\nSearch results:\n{json.dumps(combined, indent=2)}",
        )
        if isinstance(data, dict):
            if not data.get("sources"):
                data["sources"] = [
                    {"title": r["title"], "url": r["url"]} for r in combined[:5] if r.get("url")
                ]
            data["raw_results"] = combined
            return data
    except Exception as exc:
        snippet = next((r.get("snippet") for r in combined if r.get("snippet")), "")
        return {
            "subject": focus,
            "summary": snippet or f"Unable to structure overview: {exc}",
            "sources": [{"title": r["title"], "url": r["url"]} for r in combined if r.get("url")],
            "raw_results": combined,
        }

    return {"subject": focus, "sources": [], "raw_results": combined}
