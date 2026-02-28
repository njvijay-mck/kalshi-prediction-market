"""Rich terminal output for kalshi_sports_edge.

Renders odds tables, edge banners, LLM analysis, and run summaries
using the `rich` library for clean, styled terminal output.
"""

from __future__ import annotations

import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kalshi_sports_edge.models import (
    ConsolidatedReport,
    MarketData,
    OddsTable,
    ReportData,
    RunMetrics,
)

console = Console()

_EST = datetime.timezone(datetime.timedelta(hours=-5))
# NBA tip-off is typically 3 hours before the market's expected_expiration_time.
# This offset is confirmed accurate for NBA (Feb/Mar 2026) and used as a fallback
# for all sports series since Kalshi does not expose a game start time field.
_GAME_START_OFFSET = datetime.timedelta(hours=3)


def _fmt_game_start(iso_str: str | None) -> str:
    """Estimate game start time from expected_expiration_time minus 3 hours.

    Returns e.g. '~6:30 PM ET'. Uses EST (UTC-5, valid for all Feb/Mar games).
    Falls back to empty string on any error.
    """
    if not iso_str:
        return ""
    try:
        dt_utc = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        start_et = (dt_utc - _GAME_START_OFFSET).astimezone(_EST)
        hour = start_et.hour % 12 or 12
        am_pm = "AM" if start_et.hour < 12 else "PM"
        return f"~{hour}:{start_et.minute:02d} {am_pm} ET"
    except Exception:
        return ""


def _fmt_dollars(n: int) -> str:
    """Format an integer contract count as a compact dollar value string.

    Each Kalshi contract has a $1 notional value, so dollars = contracts × $1.
    """
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n}"


def _team_abbrev(market: MarketData) -> tuple[str | None, str | None]:
    """Extract 3-letter YES and NO team codes from the market and event tickers.

    YES abbreviation = last segment of market ticker (e.g. 'BOS').
    NO abbreviation  = the other team from the event ticker teams portion.
    Example: ticker 'KXNBAGAME-26FEB22BOSLAL-BOS', event 'KXNBAGAME-26FEB22BOSLAL'
             → yes_abbrev='BOS', no_abbrev='LAL'
    Returns (None, None) if parsing fails.
    """
    parts = market.ticker.split("-")
    if len(parts) < 3:
        return None, None
    yes_abbrev = parts[-1]

    ev_parts = market.event_ticker.split("-")
    if len(ev_parts) < 2:
        return yes_abbrev, None
    teams_str = ev_parts[1][7:]  # skip YYMONDD (7 chars) → e.g. 'BOSLAL'
    n = len(yes_abbrev)
    if teams_str.upper().startswith(yes_abbrev.upper()):
        no_abbrev = teams_str[n:] or None
    elif teams_str.upper().endswith(yes_abbrev.upper()):
        no_abbrev = teams_str[:-n] or None
    else:
        no_abbrev = None

    return yes_abbrev, no_abbrev


def print_market_header(market: MarketData) -> None:
    console.print(f"\n[bold cyan]{'─' * 62}[/bold cyan]")
    console.print(f"[bold white]{market.title}[/bold white]")
    game_str = market.game_date.isoformat() if market.game_date else "N/A"
    start_str = _fmt_game_start(market.expected_expiration_time)
    time_part = f"  |  Starts: {start_str}" if start_str else ""
    console.print(
        f"[dim]Ticker: {market.ticker}  |  Status: {market.status}[/dim]"
    )
    console.print(f"[dim]Game: {game_str}{time_part}[/dim]")
    if market.yes_team or market.no_team:
        yes_team_str = market.yes_team or "?"
        no_team_str = market.no_team or "?"
        console.print(
            f"[green]YES → {yes_team_str}[/green]"
            f"[dim]  |  NO → {no_team_str}[/dim]"
        )
    vol_dollars = _fmt_dollars(market.volume)
    oi_dollars = _fmt_dollars(market.open_interest)
    console.print(
        f"[dim]Volume: {market.volume:,} contracts ({vol_dollars})  |  "
        f"OI: {market.open_interest:,} contracts ({oi_dollars})[/dim]"
    )


def print_odds_table(odds_table: OddsTable) -> None:
    """Render a 6-column odds table with YES/NO rows and team abbreviations.

    The favored side (higher implied prob) is highlighted in green.
    3-letter team codes are shown in the Outcome column when available.
    A wide spread warning is shown when bid/ask spread exceeds the threshold.
    """
    market = odds_table.market
    yes_abbrev, no_abbrev = _team_abbrev(market)
    yes_label = f"YES ({yes_abbrev})" if yes_abbrev else "YES"
    no_label = f"NO  ({no_abbrev})" if no_abbrev else "NO"
    # "YES (BOS)" = 9 chars, "NO  (LAL)" = 9 chars — fits standard column width
    outcome_width = max(len(yes_label), len(no_label), 9)

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("Outcome", style="bold", width=outcome_width, no_wrap=True)
    tbl.add_column("Price (¢)", justify="right", width=10)
    tbl.add_column("Implied %", justify="right", width=10)
    tbl.add_column("Decimal", justify="right", width=9)
    tbl.add_column("American", justify="right", width=10)
    tbl.add_column("Fractional", justify="right", width=11)

    for row, label in [
        (odds_table.yes_row, yes_label),
        (odds_table.no_row, no_label),
    ]:
        style = "green" if row.implied_prob > 0.5 else ""
        tbl.add_row(
            label,
            str(row.price_cents),
            f"{row.implied_prob:.1%}",
            f"{row.decimal_odds:.3f}",
            f"{row.american_odds:+d}",
            row.fractional_str,
            style=style,
        )

    console.print(tbl)

    # Footer: overround + spread warning
    overround_color = "yellow" if abs(odds_table.overround) > 0.02 else "dim"
    footer = (
        f"[{overround_color}]Overround: {odds_table.overround:+.4f}  |  "
        f"Source: {odds_table.price_source}[/{overround_color}]"
    )
    if odds_table.wide_spread:
        spread = odds_table.market.spread_cents
        footer += f"  [yellow]⚠ Wide spread ({spread}¢ — price estimate may be imprecise)[/yellow]"
    console.print(f"  {footer}")


def print_edge_banner(report: ReportData) -> None:
    """Print RECOMMENDED POSITION panel or PASS message."""
    if report.recommended_side and report.recommended_edge is not None:
        side = report.recommended_side
        edge = report.recommended_edge
        # EV = edge / implied_prob of the recommended side
        implied = (
            report.odds_table.yes_row.implied_prob
            if side == "YES"
            else report.odds_table.no_row.implied_prob
        )
        ev = edge / implied if implied > 0 else 0.0
        content = (
            f"[bold green]RECOMMENDED POSITION: {side}[/bold green]\n"
            f"Edge: [bold]{edge:.1%}[/bold]  |  "
            f"EV: [bold]+${ev:.3f}[/bold] per $1 wagered"
        )
        panel = Panel(content, title="[bold green]★ EDGE FOUND[/bold green]", border_style="green")
    else:
        panel = Panel(
            "[dim]No significant edge detected — PASS[/dim]",
            title="[dim]Analysis Result[/dim]",
            border_style="dim",
        )
    console.print(panel)


def print_event_group(
    markets: list[MarketData],
    tables: list[OddsTable],
    reports: list[ReportData] | None = None,
    verbose: bool = False,
) -> None:
    """Print one combined block for all markets sharing the same event ticker.

    Single-market events fall back to print_report (standard YES/NO table).
    Multi-market events render a combined team table with one row per team,
    showing each team's win probability and per-team OI in compact dollar format.
    """
    if len(markets) == 1:
        r = reports[0] if reports else ReportData(market=markets[0], odds_table=tables[0])
        print_report(r, verbose=verbose)
        return

    # ── Event header ─────────────────────────────────────────────────────
    first = markets[0]
    combined_volume = sum(m.volume for m in markets)
    combined_oi = sum(m.open_interest for m in markets)

    console.print(f"\n[bold cyan]{'─' * 62}[/bold cyan]")
    console.print(f"[bold white]{first.title}[/bold white]")
    game_str = first.game_date.isoformat() if first.game_date else "N/A"
    start_str = _fmt_game_start(first.expected_expiration_time)
    time_part = f"  |  Starts: {start_str}" if start_str else ""
    console.print(f"[dim]Event: {first.event_ticker}  |  Status: {first.status}[/dim]")
    console.print(f"[dim]Game: {game_str}{time_part}[/dim]")
    vol_dollars = _fmt_dollars(combined_volume)
    oi_dollars = _fmt_dollars(combined_oi)
    console.print(
        f"[dim]Volume: {combined_volume:,} contracts ({vol_dollars})  |  "
        f"OI: {combined_oi:,} contracts ({oi_dollars})[/dim]"
    )

    # ── Combined team odds table ──────────────────────────────────────────
    # 5 data columns + Team: fits comfortably in an 80-col terminal.
    # Decimal omitted (redundant with Win%).
    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("Team", style="bold", min_width=20, no_wrap=True)
    tbl.add_column("Price (¢)", justify="right", width=9)
    tbl.add_column("Win %", justify="right", width=7)
    tbl.add_column("American", justify="right", width=10)
    tbl.add_column("Fractional", justify="right", width=11)
    tbl.add_column("OI", justify="right", width=9)

    for m, t in zip(markets, tables):
        yes_abbrev, _ = _team_abbrev(m)
        if m.yes_team and yes_abbrev:
            team_label = f"{m.yes_team} ({yes_abbrev})"
        elif m.yes_team:
            team_label = m.yes_team
        elif yes_abbrev:
            team_label = yes_abbrev
        else:
            team_label = "?"
        row = t.yes_row
        style = "green" if row.implied_prob > 0.5 else ""
        tbl.add_row(
            team_label,
            str(row.price_cents),
            f"{row.implied_prob:.1%}",
            f"{row.american_odds:+d}",
            row.fractional_str,
            _fmt_dollars(m.open_interest),
            style=style,
        )

    console.print(tbl)

    # Wide spread warnings
    wide = [
        m.yes_team or _team_abbrev(m)[0] or m.ticker
        for m, t in zip(markets, tables)
        if t.wide_spread
    ]
    if wide:
        console.print(
            f"  [yellow]⚠ Wide spread: {', '.join(str(x) for x in wide)}"
            f" — price estimate may be imprecise[/yellow]"
        )

    # ── LLM analysis + edge banners (only when LLM ran) ──────────────────
    if reports:
        for r in reports:
            if r.llm_analysis:
                yes_abbrev_r, _ = _team_abbrev(r.market)
                label = r.market.yes_team or yes_abbrev_r or r.market.ticker
                console.print(f"\n[bold yellow]── LLM: {label} ──[/bold yellow]")
                console.print(r.llm_analysis)
                print_edge_banner(r)

    if verbose and reports:
        for r in reports:
            if r.web_context:
                console.print("\n[bold dim]── Web Context ──[/bold dim]")
                console.print(r.web_context, style="dim")
                break  # shared context — print once


def print_report(report: ReportData, verbose: bool = False) -> None:
    """Print a complete single-market report: header, odds, analysis, banner."""
    print_market_header(report.market)
    print_odds_table(report.odds_table)

    if report.llm_analysis:
        console.print("\n[bold yellow]── LLM Analysis ──[/bold yellow]")
        console.print(report.llm_analysis)

    print_edge_banner(report)

    if verbose and report.web_context:
        console.print("\n[bold dim]── Web Context ──[/bold dim]")
        console.print(report.web_context, style="dim")


def print_consolidated_report(report: ConsolidatedReport, verbose: bool = False) -> None:
    """Print deep research report: all market tables + consolidation output."""
    console.print(f"\n[bold cyan]{'═' * 78}[/bold cyan]")
    console.print("[bold white]DEEP RESEARCH — CONSOLIDATED REPORT[/bold white]")
    console.print(
        f"[dim]Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  |  "
        f"Markets: {len(report.markets)}[/dim]"
    )

    for m, t in zip(report.markets, report.odds_tables):
        print_market_header(m)
        print_odds_table(t)

    if report.consolidation_output:
        console.print(f"\n[bold yellow]{'─' * 78}[/bold yellow]")
        console.print("[bold yellow]Final Analysis & Recommendations[/bold yellow]")
        console.print(report.consolidation_output)

    if verbose:
        for label, content in [
            ("Research Stage", report.research_output),
            ("Critique Stage", report.critique_output),
            ("Rebuttal Stage", report.rebuttal_output),
        ]:
            if content:
                console.print(f"\n[bold dim]── {label} ──[/bold dim]")
                console.print(content, style="dim")


def print_enhanced_consolidated_report(
    analyses: list,
    generated_at: datetime.datetime,
    model: str,
    verbose: bool = False,
) -> None:
    """Print enhanced consolidated report with all 8 sections matching PDF format.
    
    Args:
        analyses: List of MarketAnalysis objects
        generated_at: Report generation timestamp
        model: LLM model used
        verbose: Show detailed web context
    """
    from kalshi_sports_edge.models import MarketAnalysis
    
    analyses = [a for a in analyses if isinstance(a, MarketAnalysis)]
    if not analyses:
        console.print("[yellow]No analyses to display.[/yellow]")
        return
    
    # Section 1: Header
    console.print(f"\n[bold cyan]{'═' * 78}[/bold cyan]")
    console.print("[bold white]CONSOLIDATED MARKET REPORT[/bold white]")
    console.print(
        f"[dim]Generated {generated_at.strftime('%Y-%m-%d %H:%M:%S')} · "
        f"{len(analyses)} markets · {model} · deep-research[/dim]"
    )
    console.print(f"[bold cyan]{'═' * 78}[/bold cyan]")
    
    # Section 2: Summary Table
    _print_summary_table(analyses)
    
    # Section 3: Top Picks by Edge
    _print_top_picks_by_edge(analyses)
    
    # Section 4: Top Picks by EV
    _print_top_picks_by_ev(analyses)
    
    # Section 5: Markets to Avoid
    _print_markets_to_avoid(analyses)
    
    # Section 6: Mini Odds Overview
    _print_mini_odds_overview(analyses)
    
    # Section 7: Legend
    _print_why_legend()
    
    if verbose:
        console.print(f"\n[bold dim]{'─' * 78}[/bold dim]")
        console.print("[bold dim]Detailed Web Research Context[/bold dim]")
        for analysis in analyses[:3]:  # Show first 3
            console.print(f"\n[bold]{analysis.market.title}[/bold]")
            console.print(analysis.web_context[:500] + "...", style="dim")


def _by_volume_edge(a: object) -> tuple:
    """Sort key: volume descending, then |edge| descending."""
    return (-a.market.volume, -abs(a.best_edge))  # type: ignore[attr-defined]


def _game_volumes(analyses: list) -> dict[str, int]:
    """Map event_ticker → total volume (sum across both sides of a game)."""
    totals: dict[str, int] = {}
    for a in analyses:
        key = a.market.event_ticker  # type: ignore[attr-defined]
        totals[key] = totals.get(key, 0) + a.market.volume  # type: ignore[attr-defined]
    return totals


def _print_summary_table(analyses: list) -> None:
    """Print Section 2: Summary Table (All Markets)."""
    console.print("\n[bold yellow]SUMMARY TABLE[/bold yellow]")
    console.print(f"[bold cyan]{'─' * 78}[/bold cyan]")

    game_vols = _game_volumes(analyses)

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("Market", width=23, no_wrap=True)
    tbl.add_column("Game Vol", justify="right", width=9)
    tbl.add_column("Time", width=12, no_wrap=True)
    tbl.add_column("YES/NO¢", justify="center", width=9)
    tbl.add_column("Best Edge", justify="right", width=10)
    tbl.add_column("Best EV", justify="right", width=9)
    tbl.add_column("Sentiment", justify="center", width=10)
    tbl.add_column("ROI", justify="right", width=8)
    tbl.add_column("Rec", justify="center", width=6)
    tbl.add_column("Conf", justify="center", width=6)
    tbl.add_column("Why", width=10)

    for analysis in sorted(analyses, key=_by_volume_edge)[:30]:  # Top 30 by volume
        if analysis.best_edge >= 0.05:
            rec, rec_style = "BUY", "green"
        elif analysis.best_edge <= -0.05:
            rec, rec_style = "SELL", "red"
        else:
            rec, rec_style = "HOLD", "dim"

        if analysis.sentiment == "Bullish":
            sent_style = "green"
        elif analysis.sentiment == "Bearish":
            sent_style = "red"
        else:
            sent_style = "dim"

        game_vol = _fmt_dollars(
            game_vols.get(analysis.market.event_ticker, analysis.market.volume)
        )
        time_str = _fmt_game_start(analysis.market.expected_expiration_time) or "—"
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        tbl.add_row(
            analysis.market.title[:22],
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            f"{analysis.best_edge:+.2f}",
            f"{analysis.best_ev:+.3f}",
            f"[{sent_style}]{analysis.sentiment}[/{sent_style}]",
            f"{analysis.best_roi:+.1f}%",
            f"[{rec_style}]{rec}[/{rec_style}]",
            analysis.confidence,
            analysis.reason[:9],
        )

    console.print(tbl)


def _print_top_picks_by_edge(analyses: list) -> None:
    """Print Section 3: Top Picks by Edge."""
    console.print("\n[bold yellow]TOP PICKS BY EDGE[/bold yellow]")
    console.print(f"[bold cyan]{'─' * 78}[/bold cyan]")

    game_vols = _game_volumes(analyses)

    edge_picks = [a for a in analyses if abs(a.best_edge) >= 0.05]
    edge_picks.sort(key=lambda x: abs(x.best_edge), reverse=True)

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("Rank", justify="right", width=5)
    tbl.add_column("Market", width=27, no_wrap=True)
    tbl.add_column("Edge", justify="right", width=9)
    tbl.add_column("Game Vol", justify="right", width=9)
    tbl.add_column("Time", width=12, no_wrap=True)
    tbl.add_column("YES/NO¢", justify="center", width=9)
    tbl.add_column("Rec", justify="center", width=7)
    tbl.add_column("Conf", justify="center", width=6)

    for i, analysis in enumerate(edge_picks[:15], 1):
        rec = "BUY" if analysis.best_edge >= 0.05 else "SELL"
        rec_style = "green" if rec == "BUY" else "red"
        game_vol = _fmt_dollars(
            game_vols.get(analysis.market.event_ticker, analysis.market.volume)
        )
        time_str = _fmt_game_start(analysis.market.expected_expiration_time) or "—"
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        tbl.add_row(
            f"#{i}",
            analysis.market.title[:26],
            f"{analysis.best_edge*100:+.1f}%",
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            f"[{rec_style}]{rec}[/{rec_style}]",
            analysis.confidence,
        )

    console.print(tbl)


def _print_top_picks_by_ev(analyses: list) -> None:
    """Print Section 4: Top Picks by EV."""
    console.print("\n[bold yellow]TOP PICKS BY EV[/bold yellow]")
    console.print(f"[bold cyan]{'─' * 78}[/bold cyan]")

    game_vols = _game_volumes(analyses)

    ev_picks = [a for a in analyses if a.best_ev > 0]
    ev_picks.sort(key=lambda x: x.best_ev, reverse=True)

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("Rank", justify="right", width=5)
    tbl.add_column("Market", width=27, no_wrap=True)
    tbl.add_column("EV/c", justify="right", width=9)
    tbl.add_column("ROI", justify="right", width=8)
    tbl.add_column("Game Vol", justify="right", width=9)
    tbl.add_column("Time", width=12, no_wrap=True)
    tbl.add_column("YES/NO¢", justify="center", width=9)
    tbl.add_column("Rec", justify="center", width=7)

    for i, analysis in enumerate(ev_picks[:15], 1):
        game_vol = _fmt_dollars(
            game_vols.get(analysis.market.event_ticker, analysis.market.volume)
        )
        time_str = _fmt_game_start(analysis.market.expected_expiration_time) or "—"
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        tbl.add_row(
            f"#{i}",
            analysis.market.title[:26],
            f"{analysis.best_ev:+.3f}",
            f"{analysis.best_roi:+.1f}%",
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            "[green]BUY[/green]",
        )

    console.print(tbl)


def _print_markets_to_avoid(analyses: list) -> None:
    """Print Section 5: Markets to Avoid."""
    console.print("\n[bold yellow]MARKETS TO AVOID[/bold yellow]")
    console.print(f"[bold cyan]{'─' * 78}[/bold cyan]")

    game_vols = _game_volumes(analyses)

    avoid = sorted(
        [a for a in analyses if abs(a.best_edge) < 0.05 or a.best_ev <= 0],
        key=_by_volume_edge,
    )

    if not avoid:
        console.print("[dim]None — all markets show positive edge.[/dim]")
        return

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("Market", width=27, no_wrap=True)
    tbl.add_column("Game Vol", justify="right", width=9)
    tbl.add_column("Time", width=12, no_wrap=True)
    tbl.add_column("YES/NO¢", justify="center", width=9)
    tbl.add_column("Edge", justify="right", width=9)
    tbl.add_column("EV/c", justify="right", width=9)

    for analysis in avoid[:10]:
        game_vol = _fmt_dollars(
            game_vols.get(analysis.market.event_ticker, analysis.market.volume)
        )
        time_str = _fmt_game_start(analysis.market.expected_expiration_time) or "—"
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents

        tbl.add_row(
            analysis.market.title[:26],
            game_vol,
            time_str,
            f"{yes_p}/{no_p}",
            f"{analysis.best_edge*100:+.1f}%",
            f"{analysis.best_ev:+.3f}",
        )

    console.print(tbl)


def _print_mini_odds_overview(analyses: list) -> None:
    """Print Section 6: Mini Odds Overview (Per Market)."""
    console.print("\n[bold yellow]MINI ODDS OVERVIEW[/bold yellow]")
    console.print(f"[bold cyan]{'─' * 78}[/bold cyan]")

    game_vols = _game_volumes(analyses)

    for analysis in sorted(analyses, key=_by_volume_edge)[:20]:  # Top 20 by volume
        game_vol = _fmt_dollars(
            game_vols.get(analysis.market.event_ticker, analysis.market.volume)
        )
        time_str = _fmt_game_start(analysis.market.expected_expiration_time) or "—"
        yes_p = analysis.odds_table.yes_row.price_cents
        no_p = analysis.odds_table.no_row.price_cents
        console.print(f"\n[bold]{analysis.market.title}[/bold]")
        console.print(
            f"[dim]Game Vol: {game_vol}  |  {time_str}  |  "
            f"YES: {yes_p}¢  /  NO: {no_p}¢[/dim]"
        )
        
        tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
        tbl.add_column("Outcome", width=25)
        tbl.add_column("Market %", justify="right", width=10)
        tbl.add_column("LLM %", justify="right", width=10)
        tbl.add_column("Edge", justify="right", width=9)
        tbl.add_column("EV/c", justify="right", width=8)
        tbl.add_column("ROI", justify="right", width=8)
        
        # YES row
        yes_team = analysis.market.yes_team or "YES"
        yes_edge_str = f"{analysis.yes_edge*100:+.1f}%"
        yes_ev_str = f"{analysis.yes_ev:+.3f}"
        yes_roi_str = f"{analysis.yes_roi:+.1f}%"
        
        if analysis.yes_edge >= 0.05:
            yes_style = "green"
            yes_edge_str += "s"  # signal
        elif analysis.yes_edge <= -0.05:
            yes_style = "red"
            yes_edge_str += "t"  # toxic
        else:
            yes_style = ""
        
        tbl.add_row(
            f"{yes_team} (YES)",
            f"{analysis.market_yes_implied:.1%}",
            f"{analysis.llm_yes_prob:.1%}",
            yes_edge_str,
            yes_ev_str,
            yes_roi_str,
            style=yes_style,
        )
        
        # NO row
        no_team = analysis.market.no_team or "NO"
        no_edge_str = f"{analysis.no_edge*100:+.1f}%"
        no_ev_str = f"{analysis.no_ev:+.3f}"
        no_roi_str = f"{analysis.no_roi:+.1f}%"
        
        if analysis.no_edge >= 0.05:
            no_style = "green"
            no_edge_str += "s"
        elif analysis.no_edge <= -0.05:
            no_style = "red"
            no_edge_str += "t"
        else:
            no_style = ""
        
        tbl.add_row(
            f"{no_team} (NO)",
            f"{analysis.market_no_implied:.1%}",
            f"{analysis.llm_no_prob:.1%}",
            no_edge_str,
            no_ev_str,
            no_roi_str,
            style=no_style,
        )
        
        console.print(tbl)


def _print_why_legend() -> None:
    """Print Section 7: Why Column Legend."""
    console.print("\n[bold yellow]WHY COLUMN LEGEND[/bold yellow]")
    console.print(f"[bold cyan]{'─' * 78}[/bold cyan]")
    
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
    
    for key, desc in legend_items:
        console.print(f"  [bold]{key:12s}[/bold] {desc}")


def print_run_summary(metrics: RunMetrics) -> None:
    """Print a compact one-line run summary with elapsed time and error count."""
    console.print(f"\n[dim]{'─' * 62}[/dim]")
    parts = []

    # Show games if tracked, otherwise markets
    if metrics.games_analyzed > 0:
        parts.append(f"Games: {metrics.games_analyzed}")
    else:
        parts.append(f"Markets: {metrics.markets_after_filter}/{metrics.markets_fetched}")

    parts.extend([
        f"LLM calls: {metrics.llm_calls_made}",
        f"Web searches: {metrics.web_searches_made}",
    ])
    if metrics.elapsed_seconds is not None:
        parts.append(f"Time: {metrics.elapsed_seconds:.1f}s")
    console.print(f"[dim]{' | '.join(parts)}[/dim]")
    for err in metrics.errors:
        console.print(f"[red]⚠ {err}[/red]")


def print_volume_summary(
    markets: list[MarketData],
    title: str = "Games Summary (sorted by combined volume)",
) -> None:
    """Print a compact table of games grouped by event, sorted by combined volume."""
    from kalshi_sports_edge.services.market_utils import group_markets_by_game

    if not markets:
        console.print("[yellow]No markets to display.[/yellow]")
        return

    # Group markets by game (combines both sides)
    games = group_markets_by_game(markets)

    if not games:
        # Fallback: show individual markets if grouping failed
        _print_individual_markets(markets, title)
        return

    console.print(f"\n[bold cyan]{'─' * 100}[/bold cyan]")
    console.print(f"[bold white]{title}[/bold white]")
    now_str = datetime.datetime.now(_EST).strftime('%Y-%m-%d %H:%M ET')
    summary_line = (
        f"[dim]Total: {len(games)} games ({len(markets)} markets) | "
        f"Time: {now_str} | By Volume[/dim]"
    )
    console.print(summary_line)
    console.print(f"[bold cyan]{'─' * 100}[/bold cyan]")

    # Table: Rank | Event | Matchup | Time | Team A Price | Team B Price | Combined Vol | OI
    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("#", justify="right", width=3)
    tbl.add_column("Event Ticker", style="bold cyan", width=24, no_wrap=True)
    tbl.add_column("Matchup", width=22, no_wrap=True)
    tbl.add_column("Time", width=10, no_wrap=True)
    tbl.add_column("Prices (YES-NO)", justify="center", width=22)
    tbl.add_column("Volume", justify="right", width=10)

    for i, game in enumerate(games, 1):
        # Format matchup
        matchup = f"{game.team_a_abbrev} vs {game.team_b_abbrev}"

        # Game start time
        game_time = _fmt_game_start(game.expected_expiration_time) or "TBD"

        # Prices: YES-NO for each team
        # Team A YES price = X, NO price = 100-X
        # Team B YES price = Y, NO price = 100-Y
        team_a_yes = game.team_a_market.mid_price
        team_b_yes = game.team_b_market.mid_price

        if team_a_yes is not None and team_b_yes is not None:
            team_a_no = 100 - team_a_yes
            team_b_no = 100 - team_b_yes
            # Display: A: 45-55 | B: 55-45
            price_str = (
                f"[green]{game.team_a_abbrev}[/green]: {team_a_yes}-{team_a_no} | "
                f"[blue]{game.team_b_abbrev}[/blue]: {team_b_yes}-{team_b_no}"
            )
        else:
            price_str = "—"

        # Combined volume
        vol_str = _fmt_dollars(game.combined_volume)

        # Highlight started games in dim
        style = "dim" if game.has_started() else ""

        tbl.add_row(
            str(i),
            game.event_ticker,
            matchup,
            game_time,
            price_str,
            vol_str,
            style=style,
        )

    console.print(tbl)

    # Legend
    console.print("[dim]  • Prices shown as YES-NO (cents). Binary: YES + NO = 100¢[/dim]")
    console.print("[dim]  • Example: SAS: 45-55 = SAS YES at 45¢, SAS NO at 55¢[/dim]")
    console.print("[dim]  • Dimmed rows indicate games that may have already started[/dim]")


def _print_individual_markets(
    markets: list[MarketData],
    title: str = "Markets Summary",
) -> None:
    """Fallback: print individual markets when grouping fails."""
    sorted_markets = sorted(markets, key=lambda m: m.volume, reverse=True)

    console.print(f"\n[bold cyan]{'─' * 80}[/bold cyan]")
    console.print(f"[bold white]{title}[/bold white]")
    console.print(f"[dim]{len(markets)} individual markets | By Volume[/dim]")
    console.print(f"[bold cyan]{'─' * 80}[/bold cyan]")

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("#", justify="right", width=3)
    tbl.add_column("Ticker", style="bold", width=30, no_wrap=True)
    tbl.add_column("Team", width=15, no_wrap=True)
    tbl.add_column("YES", justify="right", width=6)
    tbl.add_column("NO", justify="right", width=6)
    tbl.add_column("Volume", justify="right", width=10)

    for i, m in enumerate(sorted_markets, 1):
        team = m.yes_team or "?"
        yes = m.mid_price if m.mid_price is not None else 0
        no = 100 - yes if yes else 0
        vol_str = _fmt_dollars(m.volume)
        style = "dim" if m.has_started() else ""

        tbl.add_row(
            str(i),
            m.ticker,
            team[:15],
            f"{yes}¢" if yes else "—",
            f"{no}¢" if no else "—",
            vol_str,
            style=style,
        )

    console.print(tbl)
