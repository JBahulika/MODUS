"""PDF brief generator using ReportLab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.config import get_settings


def generate_pdf(report: dict[str, Any], job_id: str) -> Path:
    settings = get_settings()
    out_path = settings.reports_path / f"{job_id}.pdf"
    subject = report.get("subject") or report.get("query") or "Enterprise Research"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"{subject} — Enterprise AI Brief",
    )
    styles = _styles()
    story: list[Any] = []

    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("Enterprise AI Research Agent", styles["brand"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(_safe(subject), styles["title"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Transformation Research Brief", styles["subtitle"]))
    story.append(Spacer(1, 0.4 * inch))
    story.append(
        Paragraph(
            "Compiled from public web and news sources with recommendation rationales.",
            styles["body"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("Executive Summary", styles["h1"]))
    story.append(Paragraph(_safe(report.get("executive_summary")), styles["body"]))

    context = report.get("context") or {}
    story.append(Paragraph("Context", styles["h1"]))
    story.append(Paragraph(_safe(context.get("company_or_subject_summary")), styles["body"]))
    if context.get("industry"):
        story.append(Paragraph(f"<b>Industry:</b> {_safe(context.get('industry'))}", styles["body"]))
    if context.get("operating_notes"):
        story.append(Paragraph(_safe(context.get("operating_notes")), styles["body"]))

    signals = report.get("industry_signals") or {}
    story.append(Paragraph("Industry Signals", styles["h1"]))
    story.append(Paragraph("Trends", styles["h2"]))
    story.append(_bullets([_safe(x) for x in (signals.get("trends") or [])], styles))
    story.append(Paragraph("AI adoption patterns", styles["h2"]))
    story.append(
        _bullets([_safe(x) for x in (signals.get("ai_adoption_patterns") or [])], styles)
    )

    story.append(Paragraph("Recent News", styles["h1"]))
    news = report.get("recent_news") or []
    if not news:
        story.append(Paragraph("No recent news captured.", styles["body"]))
    for item in news:
        story.append(
            Paragraph(
                f"<b>{_safe(item.get('headline'))}</b> ({_safe(item.get('date'))})",
                styles["body"],
            )
        )
        story.append(Paragraph(_safe(item.get("summary")), styles["body"]))
        if item.get("url"):
            url = _safe(item.get("url"))
            story.append(Paragraph(f'<link href="{url}">{url}</link>', styles["link"]))

    story.append(Paragraph("Competitors", styles["h1"]))
    for c in report.get("competitors") or []:
        story.append(Paragraph(_safe(c.get("name")), styles["h2"]))
        story.append(Paragraph(_safe(c.get("why")), styles["body"]))
        moves = c.get("ai_or_transformation_moves") or []
        if moves:
            story.append(_bullets([_safe(x) for x in moves], styles))

    story.append(Paragraph("AI Opportunities", styles["h1"]))
    for opp in report.get("ai_opportunities") or []:
        story.append(Paragraph(_safe(opp.get("title")), styles["h2"]))
        story.append(
            Paragraph(
                f"<b>Function:</b> {_safe(opp.get('process_or_function'))} · "
                f"<b>Complexity:</b> {_safe(opp.get('complexity'))}",
                styles["body"],
            )
        )
        story.append(Paragraph(_safe(opp.get("why_now")), styles["body"]))
        story.append(Paragraph(_safe(opp.get("expected_impact")), styles["body"]))

    story.append(Paragraph("Risks", styles["h1"]))
    for risk in report.get("risks") or []:
        if isinstance(risk, dict):
            story.append(
                Paragraph(
                    f"<b>{_safe(risk.get('title'))}</b> "
                    f"({_safe(risk.get('severity'))} / {_safe(risk.get('category'))})",
                    styles["body"],
                )
            )
            story.append(Paragraph(_safe(risk.get("detail")), styles["body"]))
            if risk.get("mitigation"):
                story.append(
                    Paragraph(f"<b>Mitigation:</b> {_safe(risk.get('mitigation'))}", styles["body"])
                )
        else:
            story.append(Paragraph(_safe(risk), styles["body"]))

    story.append(Paragraph("Recommendations", styles["h1"]))
    for rec in report.get("recommendations") or []:
        story.append(
            Paragraph(
                f"<b>{_safe(rec.get('title'))}</b> · priority {_safe(rec.get('priority'))} · "
                f"confidence {_safe(rec.get('confidence'))}",
                styles["h2"],
            )
        )
        story.append(Paragraph(f"<b>Why:</b> {_safe(rec.get('rationale'))}", styles["body"]))
        findings = rec.get("supporting_findings") or []
        if findings:
            story.append(Paragraph("Supporting findings", styles["h2"]))
            story.append(_bullets([_safe(x) for x in findings], styles))
        for src in rec.get("sources") or []:
            url = _safe(src.get("url"))
            if url and url != "—":
                story.append(
                    Paragraph(
                        f'• {_safe(src.get("title"))}: <link href="{url}">{url}</link>',
                        styles["link"],
                    )
                )

    notes = report.get("confidence_notes") or []
    conflicts = report.get("conflicts") or []
    if notes or conflicts:
        story.append(Paragraph("Confidence & Conflicts", styles["h1"]))
        if notes:
            story.append(_bullets([_safe(x) for x in notes], styles))
        if conflicts:
            story.append(_bullets([_safe(x) for x in conflicts], styles))

    story.append(Paragraph("Sources", styles["h1"]))
    sources = report.get("sources") or []
    if not sources:
        story.append(Paragraph("No sources recorded.", styles["body"]))
    for src in sources:
        title = _safe(src.get("title"))
        url = _safe(src.get("url"))
        story.append(Paragraph(f"• {title}", styles["body"]))
        if url and url != "—":
            story.append(Paragraph(f'<link href="{url}">{url}</link>', styles["link"]))

    doc.build(story)
    return out_path


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "brand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#0f4c5c"),
            alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=colors.HexColor("#102a43"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=14,
            textColor=colors.HexColor("#486581"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=colors.HexColor("#102a43"),
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.HexColor("#243b53"),
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#243b53"),
            spaceAfter=6,
        ),
        "link": ParagraphStyle(
            "link",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#0b6e4f"),
            spaceAfter=8,
        ),
    }


def _bullets(items: list[str], styles: dict[str, ParagraphStyle]) -> Any:
    items = [i for i in items if i and i != "—"]
    if not items:
        return Paragraph("None listed.", styles["body"])
    return ListFlowable(
        [ListItem(Paragraph(i, styles["body"])) for i in items],
        bulletType="bullet",
        leftIndent=12,
    )


def _safe(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (list, tuple)):
        parts = [str(v).strip() for v in value if v is not None and str(v).strip()]
        return ", ".join(parts) if parts else "—"
    text = str(value).strip()
    if not text:
        return "—"
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
