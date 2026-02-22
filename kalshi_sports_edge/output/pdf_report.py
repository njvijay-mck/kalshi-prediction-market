"""PDF report generation using reportlab (pure Python, no system dependencies).

Single-market reports: reports/YYYY-MM-DD/{ticker}.pdf
Consolidated reports:  reports/YYYY-MM-DD/consolidated_{HHMMSS}.pdf

reportlab uses points (1/72 inch). All sizing constants are in points.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from kalshi_sports_edge.models import ConsolidatedReport, OddsTable, ReportData

# ---------------------------------------------------------------------------
# Style definitions (defined once, reused across all reports)
# ---------------------------------------------------------------------------

_BASE = getSampleStyleSheet()

_TITLE = ParagraphStyle(
    "kse_title", parent=_BASE["Title"], fontSize=16, spaceAfter=8, alignment=TA_CENTER
)
_H2 = ParagraphStyle(
    "kse_h2", parent=_BASE["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=6
)
_BODY = ParagraphStyle(
    "kse_body", parent=_BASE["BodyText"], fontSize=10, spaceAfter=5, leading=14
)
_SMALL = ParagraphStyle(
    "kse_small", parent=_BASE["BodyText"], fontSize=9, spaceAfter=3, leading=12
)
_REC = ParagraphStyle(
    "kse_rec", parent=_BASE["Heading2"], fontSize=12, textColor=colors.HexColor("#1a7a1a"),
    spaceBefore=10, spaceAfter=6
)

# Odds table column widths (points)
_COL_WIDTHS = [60, 55, 65, 60, 65, 65]

# Header background color
_HEADER_BG = colors.HexColor("#1f3864")
_ROW_A = colors.HexColor("#f0f4fb")
_ROW_B = colors.white


def write_single_report(report: ReportData, output_dir: str = "reports") -> Path:
    """Write a single-market PDF report. Returns the Path to the file."""
    path = _ensure_output_dir(output_dir) / f"{report.market.ticker}.pdf"
    doc = SimpleDocTemplate(
        str(path), pagesize=letter,
        leftMargin=inch, rightMargin=inch,
        topMargin=inch, bottomMargin=inch,
    )

    story = []
    m = report.market

    story.append(Paragraph("Kalshi Sports Edge", _TITLE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(m.title, _H2))
    story.append(Paragraph(
        f"Ticker: <b>{m.ticker}</b>  |  Status: {m.status}  |  Close: {m.close_time or 'N/A'}",
        _SMALL
    ))
    story.append(Paragraph(
        f"Volume: {m.volume:,} contracts  |  Open Interest: {m.open_interest:,} contracts",
        _SMALL
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Odds Table", _H2))
    story.append(_build_odds_table_element(report.odds_table))
    story.append(Paragraph(
        f"Overround: {report.odds_table.overround:+.4f}  |  "
        f"Price source: {report.odds_table.price_source}"
        + ("  ⚠ Wide spread" if report.odds_table.wide_spread else ""),
        _SMALL
    ))

    if report.llm_analysis:
        story.append(Spacer(1, 10))
        story.append(Paragraph("LLM Analysis", _H2))
        for line in report.llm_analysis.split("\n"):
            stripped = line.strip()
            if stripped:
                story.append(Paragraph(stripped, _BODY))

    if report.recommended_side and report.recommended_edge is not None:
        story.append(Spacer(1, 10))
        implied = (
            report.odds_table.yes_row.implied_prob
            if report.recommended_side == "YES"
            else report.odds_table.no_row.implied_prob
        )
        ev = report.recommended_edge / implied if implied > 0 else 0.0
        story.append(Paragraph(
            f"★ RECOMMENDED POSITION: {report.recommended_side}  |  "
            f"Edge: {report.recommended_edge:.1%}  |  EV: ${ev:.3f} per $1",
            _REC
        ))

    doc.build(story)
    return path


def write_consolidated_report(report: ConsolidatedReport, output_dir: str = "reports") -> Path:
    """Write a multi-market deep research PDF report. Returns the Path."""
    ts = report.generated_at.strftime("%H%M%S")
    path = _ensure_output_dir(output_dir) / f"consolidated_{ts}.pdf"

    doc = SimpleDocTemplate(
        str(path), pagesize=letter,
        leftMargin=inch, rightMargin=inch,
        topMargin=inch, bottomMargin=inch,
    )

    story = []
    story.append(Paragraph("Kalshi Sports Edge — Deep Research Report", _TITLE))
    story.append(Paragraph(
        f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  |  "
        f"Markets analyzed: {len(report.markets)}",
        _SMALL
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Market Odds Summary", _H2))
    for m, t in zip(report.markets, report.odds_tables):
        story.append(Paragraph(f"{m.title}  ({m.ticker})", _H2))
        story.append(Paragraph(
            f"Volume: {m.volume:,} | OI: {m.open_interest:,} | Close: {m.close_time or 'N/A'}",
            _SMALL
        ))
        story.append(_build_odds_table_element(t))
        story.append(Spacer(1, 6))

    if report.consolidation_output:
        story.append(Paragraph("Final Analysis & Recommendations", _H2))
        for line in report.consolidation_output.split("\n"):
            stripped = line.strip()
            if stripped:
                story.append(Paragraph(stripped, _BODY))

    doc.build(story)
    return path


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _ensure_output_dir(output_dir: str) -> Path:
    date_str = datetime.date.today().isoformat()
    path = Path(output_dir) / date_str
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_odds_table_element(t: OddsTable) -> Table:
    """Build a reportlab Table for one OddsTable (2 data rows + header)."""
    header = ["Outcome", "Price (¢)", "Implied %", "Decimal", "American", "Fractional"]
    rows = [header]
    for row in [t.yes_row, t.no_row]:
        rows.append([
            row.outcome,
            str(row.price_cents),
            f"{row.implied_prob:.1%}",
            f"{row.decimal_odds:.3f}",
            f"{row.american_odds:+d}",
            row.fractional_str,
        ])

    tbl = Table(rows, colWidths=_COL_WIDTHS)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_A, _ROW_B]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl
