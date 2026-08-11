"""Post-process reports: rank sources, filter competitors, attach eval metrics."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


_GENERIC_COMPETITOR = re.compile(
    r"^(leading|advanced|specialized|typical|regional|digital-first|innovator)\b|"
    r"\b(bank|institution|player|competitor)\s*$",
    re.I,
)


def enrich_report(report: dict[str, Any], *, latency_ms: int | None = None) -> dict[str, Any]:
    report = dict(report)
    report["competitors"] = _named_competitors(report.get("competitors") or [])
    report["sources"] = _rank_sources(report.get("sources") or [])[:12]
    report["claims"] = report.get("claims") or _derive_claims(report)
    report["overall_confidence"] = report.get("overall_confidence") or _overall_confidence(report)
    report["confidence_score"] = report.get("confidence_score") or _confidence_score(report)
    report["one_pager"] = report.get("one_pager") or _one_pager(report)
    report["agent_contributions"] = report.get("agent_contributions") or []
    report["eval"] = _build_eval(report, latency_ms=latency_ms)
    report["roadmap"] = report.get("roadmap") or {
        "now": ["Multi-agent research", "Source-backed recommendations", "Risk pass", "PDF export"],
        "next": ["Worker queue + Postgres", "Internal system connectors", "Claim-level citation graph"],
        "later": ["Live operating-model sync", "Portfolio what-if simulation", "Role-based governed actions"],
    }
    report["recommendations"] = [
        _normalize_rec(rec) for rec in (report.get("recommendations") or []) if isinstance(rec, dict)
    ]
    return report


def _normalize_rec(rec: dict[str, Any]) -> dict[str, Any]:
    roles = rec.get("roles") or ["coo", "risk", "transformation"]
    return {
        **rec,
        "roles": roles,
        "supporting_findings": rec.get("supporting_findings") or [],
        "sources": rec.get("sources") or [],
        "confidence": rec.get("confidence") or "medium",
        "priority": rec.get("priority") or "medium",
    }


def _named_competitors(items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if _is_generic_name(name):
            continue
        out.append(item)
    return out


def _is_generic_name(name: str) -> bool:
    lowered = name.lower().strip()
    if any(
        token in lowered
        for token in (
            "leading digital",
            "advanced regional",
            "specialized lending",
            "compliance & fraud innovator",
            "represents banks",
            "typical mid",
            "peer bank",
        )
    ):
        return True
    # Require at least one capitalised proper-looking token and not only category words
    if len(name.split()) >= 4 and not any(c.isupper() for c in name[1:]):
        return True
    return False


def _rank_sources(sources: list[Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    ranked: list[dict[str, Any]] = []
    for idx, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        url = (src.get("url") or "").strip()
        title = (src.get("title") or url or "Source").strip()
        key = url or title.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        domain = urlparse(url).netloc.replace("www.", "") if url else ""
        score = 0
        if domain:
            score += 2
        if any(
            d in domain
            for d in (
                "mckinsey",
                "deloitte",
                "bcg",
                "gartner",
                "harvard",
                "reuters",
                "ft.com",
                "wsj",
                "americanbanker",
                "federalreserve",
                "bis.org",
            )
        ):
            score += 5
        ranked.append(
            {
                "id": src.get("id") or f"s{len(ranked) + 1}",
                "title": title,
                "url": url,
                "rank": 0,
                "domain": domain,
                "_score": score,
                "_order": idx,
            }
        )
    ranked.sort(key=lambda s: (-s["_score"], s["_order"]))
    out = []
    for i, item in enumerate(ranked, start=1):
        item["rank"] = i
        item.pop("_score", None)
        item.pop("_order", None)
        out.append(item)
    return out


def _derive_claims(report: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    summary = str(report.get("executive_summary") or "").strip()
    sources = report.get("sources") or []
    source_ids = [s.get("id") for s in sources[:3] if isinstance(s, dict) and s.get("id")]
    if summary:
        first = summary.split(". ")[0].strip()
        if first:
            claims.append(
                {
                    "id": "c1",
                    "text": first if first.endswith(".") else first + ".",
                    "source_ids": source_ids[:2],
                }
            )
    for i, rec in enumerate((report.get("recommendations") or [])[:2]):
        if not isinstance(rec, dict):
            continue
        rationale = str(rec.get("rationale") or "").strip()
        if not rationale:
            continue
        rec_sources = rec.get("sources") or []
        ids = []
        for s in rec_sources:
            if isinstance(s, dict) and s.get("id"):
                ids.append(s["id"])
            elif isinstance(s, dict) and s.get("url"):
                for top in sources:
                    if isinstance(top, dict) and top.get("url") == s.get("url") and top.get("id"):
                        ids.append(top["id"])
        claims.append(
            {
                "id": f"c{i + 2}",
                "text": rationale.split(". ")[0].strip().rstrip(".") + ".",
                "source_ids": ids[:3] or source_ids[:2],
            }
        )
    return claims


def _overall_confidence(report: dict[str, Any]) -> str:
    notes = " ".join(str(x) for x in (report.get("confidence_notes") or [])).lower()
    if "thin" in notes or "incomplete" in notes or "low" in notes:
        return "medium"
    if len(report.get("sources") or []) >= 5 and len(report.get("recommendations") or []) >= 3:
        return "high"
    return "medium"


def _confidence_score(report: dict[str, Any]) -> float:
    level = str(report.get("overall_confidence") or "medium")
    base = {"high": 0.8, "medium": 0.62, "low": 0.4}.get(level, 0.62)
    sources = len(report.get("sources") or [])
    conflicts = len(report.get("conflicts") or [])
    score = base + min(0.12, sources * 0.01) - min(0.2, conflicts * 0.05)
    return round(max(0.2, min(0.95, score)), 2)


def _one_pager(report: dict[str, Any]) -> dict[str, Any]:
    recs = [
        str(r.get("title"))
        for r in (report.get("recommendations") or [])
        if isinstance(r, dict) and r.get("title")
    ][:3]
    risks = []
    for r in (report.get("risks") or [])[:3]:
        if isinstance(r, dict):
            risks.append(str(r.get("title") or ""))
        else:
            risks.append(str(r))
    summary = str(report.get("executive_summary") or "")
    headline = summary.split(". ")[0].strip()
    if len(headline) > 110:
        headline = headline[:107] + "..."
    return {
        "headline": headline or str(report.get("subject") or "Transformation brief"),
        "three_moves": recs,
        "watchouts": [x for x in risks if x],
    }


def _build_eval(report: dict[str, Any], latency_ms: int | None = None) -> dict[str, Any]:
    sources = report.get("sources") or []
    claims = report.get("claims") or []
    linked = sum(1 for c in claims if isinstance(c, dict) and c.get("source_ids"))
    risks = report.get("risks") or []
    has_mitigations = any(isinstance(r, dict) and r.get("mitigation") for r in risks)
    return {
        "sources_count": len(sources),
        "claims_linked": linked,
        "recommendations_count": len(report.get("recommendations") or []),
        "named_competitors": len(report.get("competitors") or []),
        "conflicts_count": len(report.get("conflicts") or []),
        "has_risk_mitigations": has_mitigations,
        "latency_ms": latency_ms,
        "latency_note": f"{latency_ms} ms" if latency_ms is not None else "n/a",
    }
