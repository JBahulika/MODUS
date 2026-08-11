"""PDF brief generator using ReportLab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
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
    Table,
    TableStyle,
)

from app.config import get_settings


def generate_pdf(report: dict[str, Any], job_id: str) -> Path:
    settings = get_settings()
    out_path = settings.reports_path / f"{job_id}.pdf"
    subject = report.get("subject") or report.get("query") or "Enterprise Research"
    one = report.get("one_pager") or {}

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{subject} — Enterprise AI Brief",
    )
    styles = _styles()
    story: list[Any] = []

    story.append(Paragraph("Enterprise AI Research Agent", styles["brand"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(_safe(subject), styles["title"]))
    story.append(Paragraph("Transformation Research Brief", styles["subtitle"]))
    story.append(Spacer(1, 0.25 * inch))

    conf = report.get("overall_confidence") or "medium"
    score = report.get("confidence_score")
    score_txt = f"{int(float(score) * 100)}%" if score is not None else "—"
    story.append(
        _meta_table(
            [
                ["Confidence", f"{conf} ({score_txt})"],
                ["Industry", _safe((report.get("context") or {}).get("industry"))],
                ["Sources", str(len(report.get("sources") or []))],
            ]
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("One-page brief", styles["h1"]))
    story.append(Paragraph(_safe(one.get("headline") or report.get("executive_summary")), styles["body"]))
    story.append(Paragraph("Three moves", styles["h2"]))
    story.append(_bullets([_safe(x) for x in (one.get("three_moves") or [])], styles))
    story.append(Paragraph("Watchouts", styles["h2"]))
    story.append(_bullets([_safe(x) for x in (one.get("watchouts") or [])], styles))
    story.append(PageBreak())

    story.append(Paragraph("Executive Summary", styles["h1"]))
    story.append(Paragraph(_safe(report.get("executive_summary")), styles["body"]))

    if report.get("what_if_assessment") or report.get("what_if"):
        story.append(Paragraph("What-if assessment", styles["h1"]))
        story.append(
            Paragraph(
                _safe(report.get("what_if_assessment") or report.get("what_if")),
                styles["body"],
            )
        )

    story.append(Paragraph("Recommendations", styles["h1"]))
    for rec in report.get("recommendations") or []:
        story.append(
            Paragraph(
                f"<b>{_safe(rec.get('title'))}</b> · {_safe(rec.get('priority'))} priority · "
                f"{_safe(rec.get('confidence'))} confidence",
                styles["h2"],
            )
        )
        story.append(Paragraph(f"<b>Why:</b> {_safe(rec.get('rationale'))}", styles["body"]))
        story.append(_bullets([_safe(x) for x in (rec.get("supporting_findings") or [])], styles))

    story.append(Paragraph("Named competitors", styles["h1"]))
    for c in report.get("competitors") or []:
        story.append(Paragraph(_safe(c.get("name")), styles["h2"]))
        story.append(Paragraph(_safe(c.get("why")), styles["body"]))

    story.append(Paragraph("Risks", styles["h1"]))
    for risk in report.get("risks") or []:
        if isinstance(risk, dict):
            story.append(
                Paragraph(
                    f"<b>{_safe(risk.get('title'))}</b> ({_safe(risk.get('severity'))})",
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

    story.append(Paragraph("Sources", styles["h1"]))
    for src in (report.get("sources") or [])[:12]:
        title = _safe(src.get("title"))
        url = _safe(src.get("url"))
        story.append(Paragraph(f"• {title}", styles["body"]))
        if url and url != "—":
            story.append(Paragraph(f'<link href="{url}">{url}</link>', styles["link"]))

    roadmap = report.get("roadmap") or {}
    if roadmap:
        story.append(Paragraph("Roadmap", styles["h1"]))
        for key in ("now", "next", "later"):
            story.append(Paragraph(key.title(), styles["h2"]))
            story.append(_bullets([_safe(x) for x in (roadmap.get(key) or [])], styles))

    doc.build(story)
    return out_path


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "brand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.HexColor("#1f4d3a"),
            alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.HexColor("#1c1914"),
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            textColor=colors.HexColor("#5c564c"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#1c1914"),
            spaceBefore=12,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.HexColor("#1f4d3a"),
            spaceBefore=8,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#2a2620"),
            spaceAfter=5,
        ),
        "link": ParagraphStyle(
            "link",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#9a4c1d"),
            spaceAfter=6,
        ),
    }


def _meta_table(rows: list[list[str]]) -> Table:
    cleaned = [[a, b or "—"] for a, b in rows]
    table = Table(cleaned, colWidths=[1.5 * inch, 5.3 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3efe6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9d0c0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9d0c0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


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
