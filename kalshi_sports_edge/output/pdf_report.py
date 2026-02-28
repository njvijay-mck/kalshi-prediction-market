"""PDF report generation using reportlab (pure Python, no system dependencies).

Single-market reports: reports/YYYY-MM-DD/{ticker}.pdf
Consolidated reports:  reports/YYYY-MM-DD/consolidated_{HHMMSS}.pdf

reportlab uses points (1/72 inch). All sizing constants are in points.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from kalshi_sports_edge.models import ConsolidatedReport, MarketAnalysis, OddsTable, ReportData

# ---------------------------------------------------------------------------
# Style definitions (defined once, reused across all reports)
# ---------------------------------------------------------------------------

_BASE = getSampleStyleSheet()

_TITLE = ParagraphStyle(
    "kse_title", parent=_BASE["Title"], fontSize=18, spaceAfter=8, alignment=TA_CENTER,
    textColor=colors.HexColor("#1f3864")
)
_H1 = ParagraphStyle(
    "kse_h1", parent=_BASE["Heading1"], fontSize=14, spaceBefore=16, spaceAfter=8,
    textColor=colors.HexColor("#1f3864")
)
_H2 = ParagraphStyle(
    "kse_h2", parent=_BASE["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=6,
    textColor=colors.HexColor("#1f3864")
)
_H3 = ParagraphStyle(
    "kse_h3", parent=_BASE["Heading3"], fontSize=10, spaceBefore=8, spaceAfter=4,
    textColor=colors.HexColor("#1f3864")
)
_BODY = ParagraphStyle(
    "kse_body", parent=_BASE["BodyText"], fontSize=9, spaceAfter=4, leading=12
)
_SMALL = ParagraphStyle(
    "kse_small", parent=_BASE["BodyText"], fontSize=8, spaceAfter=2, leading=10
)
_REC = ParagraphStyle(
    "kse_rec", parent=_BASE["Heading2"], fontSize=11, textColor=colors.HexColor("#1a7a1a"),
    spaceBefore=8, spaceAfter=4
)
_WARN = ParagraphStyle(
    "kse_warn", parent=_BASE["BodyText"], fontSize=9, textColor=colors.HexColor("#8b4513"),
    spaceAfter=3
)

# Table column widths (points). Usable page width ≈ 504 pts (7" with 0.75" margins).
_COL_WIDTHS_ODDS = [60, 55, 65, 60, 65, 65]
# Market|GameVol|Time|YES/NO|Edge|EV|Sentiment|ROI|Rec|Conf|Why  → 469 pts
_COL_WIDTHS_SUMMARY = [60, 44, 56, 38, 42, 40, 48, 34, 32, 32, 43]
# Rank|Market|Edge|GameVol|Time|YES/NO|Rec|Conf  → 398 pts
_COL_WIDTHS_TOP_PICKS = [25, 100, 44, 50, 58, 40, 38, 43]
# Market|GameVol|Time|YES/NO|Edge|EV  → 344 pts
_COL_WIDTHS_AVOID = [100, 50, 62, 44, 44, 44]
_COL_WIDTHS_MINI = [90, 55, 55, 50, 45, 45]

# Header background color
_HEADER_BG = colors.HexColor("#1f3864")
_ROW_A = colors.HexColor("#f0f4fb")
_ROW_B = colors.white
_GREEN_BG = colors.HexColor("#d4edda")
_RED_BG = colors.HexColor("#f8d7da")
_YELLOW_BG = colors.HexColor("#fff3cd")


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
    """Write a multi-market deep research PDF report (legacy format)."""
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


def write_enhanced_consolidated_report(
    analyses: list[MarketAnalysis],
    generated_at: datetime.datetime,
    model: str,
    output_dir: str = "reports",
) -> Path:
    """Write an enhanced multi-market PDF report with all 8 sections.
    
    Args:
        analyses: List of MarketAnalysis objects
        generated_at: Report generation timestamp
        model: LLM model used
        output_dir: Output directory for reports
    
    Returns:
        Path to the generated PDF file
    """
    ts = generated_at.strftime("%H%M%S")
    path = _ensure_output_dir(output_dir) / f"consolidated_{ts}.pdf"

    doc = SimpleDocTemplate(
        str(path), pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
    )

    story = []
    
    # Section 1: Header
    story.append(Paragraph("CONSOLIDATED MARKET REPORT", _TITLE))
    story.append(Paragraph(
        f"Generated {generated_at.strftime('%Y-%m-%d %H:%M:%S')} · "
        f"{len(analyses)} markets · {model} · deep-research",
        _SMALL
    ))
    story.append(Spacer(1, 16))
    
    # Section 2: Summary Table
    story.append(Paragraph("SUMMARY TABLE", _H1))
    story.append(_build_summary_table(analyses))
    story.append(Spacer(1, 12))
    
    # Section 3: Top Picks by Edge
    story.append(Paragraph("TOP PICKS BY EDGE (|Edge| >= 5%)", _H1))
    story.append(_build_top_picks_by_edge_table(analyses))
    story.append(Spacer(1, 12))
    
    # Section 4: Top Picks by EV
    story.append(Paragraph("TOP PICKS BY EV (Positive EV Only)", _H1))
    story.append(_build_top_picks_by_ev_table(analyses))
    story.append(Spacer(1, 12))
    
    # Section 5: Markets to Avoid
    story.append(Paragraph("MARKETS TO AVOID", _H1))
    story.extend(_build_markets_to_avoid(analyses))
    story.append(Spacer(1, 12))
    
    # Page break before detailed odds
    story.append(PageBreak())
    
    # Section 6: Mini Odds Overview
    story.append(Paragraph("MINI ODDS OVERVIEW (Per Market)", _H1))
    story.extend(_build_mini_odds_overview(analyses))
    
    # Section 7: Legend
    story.append(Spacer(1, 16))
    story.append(Paragraph("WHY COLUMN LEGEND", _H1))
    story.extend(_build_why_legend())
    
    # Section 8: Footer/Disclaimer
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Generated by Kalshi Sports Edge · For informational purposes only · "
        "Trading involves risk of loss",
        ParagraphStyle(
            "footer", parent=_SMALL, alignment=TA_CENTER,
            textColor=colors.gray, fontSize=8
        )
    ))

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

    tbl = Table(rows, colWidths=_COL_WIDTHS_ODDS)
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


_EST_OFFSET = datetime.timezone(datetime.timedelta(hours=-5))


def _fmt_game_time(iso_str: str | None) -> str:
    """Format estimated game start time (expiration − 3 h) as '~6:30 PM ET'."""
    if not iso_str:
        return "—"
    try:
        dt_utc = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        start_et = (dt_utc - datetime.timedelta(hours=3)).astimezone(_EST_OFFSET)
        hour = start_et.hour % 12 or 12
        am_pm = "AM" if start_et.hour < 12 else "PM"
        return f"~{hour}:{start_et.minute:02d} {am_pm} ET"
    except Exception:
        return "—"


def _fmt_vol(n: int) -> str:
    """Format integer contract count as compact dollar string."""
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n}"


def _game_volumes(analyses: list[MarketAnalysis]) -> dict[str, int]:
    """Map event_ticker → total volume (sum across both sides of a game)."""
    totals: dict[str, int] = {}
    for a in analyses:
        totals[a.market.event_ticker] = totals.get(a.market.event_ticker, 0) + a.market.volume
    return totals


def _by_volume_edge(a: MarketAnalysis) -> tuple:
    """Sort key: volume descending, then |edge| descending."""
    return (-a.market.volume, -abs(a.best_edge))


def _build_summary_table(analyses: list[MarketAnalysis]) -> Table:
    """Build Section 2: Summary Table."""
    game_vols = _game_volumes(analyses)
    header = ["Market", "Game Vol", "Time", "YES/NO¢", "Best Edge", "Best EV",
              "Sentiment", "ROI", "Rec", "Conf", "Why"]
    rows = [header]

    for analysis in sorted(analyses, key=_by_volume_edge)[:30]:  # Top 30 by volume
        if analysis.best_edge >= 0.05:
            rec = "BUY"
        elif analysis.best_edge <= -0.05:
            rec = "SELL"
        else:
            rec = "HOLD"

        game_vol = _fmt_vol(game_vols.get(analysis.market.event_ticker, analysis.market.volume))
        time_str = _fmt_game_time(analysis.market.expected_expiration_time)
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        rows.append([
            analysis.market.title[:22],
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            f"{analysis.best_edge:+.2f}",
            f"{analysis.best_ev:+.3f}",
            analysis.sentiment,
            f"{analysis.best_roi:+.1f}%",
            rec,
            analysis.confidence,
            analysis.reason[:8],
        ])

    tbl = Table(rows, colWidths=_COL_WIDTHS_SUMMARY)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_A, _ROW_B]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TEXTCOLOR", (8, 1), (8, -1), _get_rec_color),
    ]))
    return tbl


def _build_top_picks_by_edge_table(analyses: list[MarketAnalysis]) -> Table:
    """Build Section 3: Top Picks by Edge."""
    game_vols = _game_volumes(analyses)
    header = ["Rank", "Market", "Edge", "Game Vol", "Time", "YES/NO¢", "Rec", "Conf"]
    rows = [header]

    edge_picks = [a for a in analyses if abs(a.best_edge) >= 0.05]
    edge_picks.sort(key=lambda x: abs(x.best_edge), reverse=True)

    for i, analysis in enumerate(edge_picks[:15], 1):
        rec = "BUY" if analysis.best_edge >= 0.05 else "SELL"
        game_vol = _fmt_vol(game_vols.get(analysis.market.event_ticker, analysis.market.volume))
        time_str = _fmt_game_time(analysis.market.expected_expiration_time)
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        rows.append([
            f"#{i}",
            analysis.market.title[:26],
            f"{analysis.best_edge*100:+.1f}%",
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            rec,
            analysis.confidence,
        ])

    tbl = Table(rows, colWidths=_COL_WIDTHS_TOP_PICKS)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_A, _ROW_B]),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _build_top_picks_by_ev_table(analyses: list[MarketAnalysis]) -> Table:
    """Build Section 4: Top Picks by EV."""
    game_vols = _game_volumes(analyses)
    header = ["Rank", "Market", "EV/c", "ROI", "Game Vol", "Time", "YES/NO¢", "Rec"]
    rows = [header]

    ev_picks = [a for a in analyses if a.best_ev > 0]
    ev_picks.sort(key=lambda x: x.best_ev, reverse=True)

    for i, analysis in enumerate(ev_picks[:15], 1):
        game_vol = _fmt_vol(game_vols.get(analysis.market.event_ticker, analysis.market.volume))
        time_str = _fmt_game_time(analysis.market.expected_expiration_time)
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        rows.append([
            f"#{i}",
            analysis.market.title[:26],
            f"{analysis.best_ev:+.3f}",
            f"{analysis.best_roi:+.1f}%",
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            "BUY",
        ])

    tbl = Table(rows, colWidths=_COL_WIDTHS_TOP_PICKS)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_A, _ROW_B]),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _build_markets_to_avoid(analyses: list[MarketAnalysis]) -> list:
    """Build Section 5: Markets to Avoid."""
    game_vols = _game_volumes(analyses)
    avoid = sorted(
        [a for a in analyses if abs(a.best_edge) < 0.05 or a.best_ev <= 0],
        key=_by_volume_edge,
    )

    if not avoid:
        return [Paragraph("None — all markets show positive edge.", _BODY)]

    header = ["Market", "Game Vol", "Time", "YES/NO¢", "Edge", "EV/c"]
    rows = [header]

    for analysis in avoid[:10]:
        game_vol = _fmt_vol(game_vols.get(analysis.market.event_ticker, analysis.market.volume))
        time_str = _fmt_game_time(analysis.market.expected_expiration_time)
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        rows.append([
            analysis.market.title[:28],
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            f"{analysis.best_edge*100:+.1f}%",
            f"{analysis.best_ev:+.3f}",
        ])

    tbl = Table(rows, colWidths=_COL_WIDTHS_AVOID)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_A, _ROW_B]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [tbl]


def _build_mini_odds_overview(analyses: list[MarketAnalysis]) -> list:
    """Build Section 6: Mini Odds Overview (per market)."""
    game_vols = _game_volumes(analyses)
    elements = []

    for analysis in sorted(analyses, key=_by_volume_edge)[:20]:  # Top 20 by volume
        game_vol = _fmt_vol(game_vols.get(analysis.market.event_ticker, analysis.market.volume))
        time_str = _fmt_game_time(analysis.market.expected_expiration_time)
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents
        elements.append(Paragraph(f"<b>{analysis.market.title}</b>", _H3))
        elements.append(Paragraph(
            f"Game Vol: {game_vol}  |  {time_str}  |  YES: {yes_p}¢  /  NO: {no_p}¢",
            _SMALL,
        ))

        header = ["Outcome", "Market %", "LLM %", "Edge", "EV/c", "ROI"]
        rows = [header]
        
        # YES row
        yes_team = analysis.market.yes_team or "YES"
        yes_edge_str = f"{analysis.yes_edge*100:+.1f}%"
        yes_style = None
        
        if analysis.yes_edge >= 0.05:
            yes_style = _GREEN_BG
        elif analysis.yes_edge <= -0.05:
            yes_style = _RED_BG
        
        rows.append([
            f"{yes_team} (YES)",
            f"{analysis.market_yes_implied:.1%}",
            f"{analysis.llm_yes_prob:.1%}",
            yes_edge_str,
            f"{analysis.yes_ev:+.3f}",
            f"{analysis.yes_roi:+.1f}%",
        ])
        
        # NO row
        no_team = analysis.market.no_team or "NO"
        no_edge_str = f"{analysis.no_edge*100:+.1f}%"
        no_style = None
        
        if analysis.no_edge >= 0.05:
            no_style = _GREEN_BG
        elif analysis.no_edge <= -0.05:
            no_style = _RED_BG
        
        rows.append([
            f"{no_team} (NO)",
            f"{analysis.market_no_implied:.1%}",
            f"{analysis.llm_no_prob:.1%}",
            no_edge_str,
            f"{analysis.no_ev:+.3f}",
            f"{analysis.no_roi:+.1f}%",
        ])
        
        tbl = Table(rows, colWidths=_COL_WIDTHS_MINI)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_A, _ROW_B]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
        
        # Apply conditional background colors
        if yes_style:
            style.add("BACKGROUND", (0, 1), (-1, 1), yes_style)
        if no_style:
            style.add("BACKGROUND", (0, 2), (-1, 2), no_style)
        
        tbl.setStyle(style)
        elements.append(tbl)
        elements.append(Spacer(1, 8))
    
    return elements


def _build_why_legend() -> list:
    """Build Section 7: Why Column Legend."""
    legend_items = [
        ("stats", "Team/player statistics drove the estimate"),
        ("injury", "Player injury status is the key variable"),
        ("form", "Recent form/performance trend is decisive"),
        ("news", "Breaking news materially changes the outlook"),
        ("data", "Market or historical base-rate data used"),
        ("record", "Head-to-head record is the main reference"),
        ("consensus", "Expert or public consensus is the anchor"),
        ("volume", "Trading volume signals informed positioning"),
        ("schedule", "Schedule strength or matchup context"),
        ("weather", "Weather/field conditions are the swing factor"),
        ("momentum", "Recent momentum swing is the key signal"),
        ("unclear", "Insufficient information to be confident"),
    ]
    
    elements = []
    for key, desc in legend_items:
        elements.append(Paragraph(f"<b>{key:12s}</b> {desc}", _SMALL))
    
    return elements


def _get_rec_color(canvas, table, row, col, x, y, w, h):
    """Callback to color recommendation cells."""
    text = table._cellvalues[row][col]
    if text == "BUY":
        return colors.HexColor("#1a7a1a")
    elif text == "SELL":
        return colors.HexColor("#8b1a1a")
    return colors.black
