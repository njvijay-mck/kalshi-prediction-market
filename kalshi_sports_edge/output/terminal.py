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
    console.print(f"\n[bold cyan]{'═' * 62}[/bold cyan]")
    console.print("[bold white]DEEP RESEARCH — CONSOLIDATED REPORT[/bold white]")
    console.print(
        f"[dim]Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  |  "
        f"Markets: {len(report.markets)}[/dim]"
    )

    for m, t in zip(report.markets, report.odds_tables):
        print_market_header(m)
        print_odds_table(t)

    if report.consolidation_output:
        console.print(f"\n[bold yellow]{'─' * 62}[/bold yellow]")
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
