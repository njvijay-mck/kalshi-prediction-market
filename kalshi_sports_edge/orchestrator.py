"""Top-level coordinator for kalshi_sports_edge.

Owns RunMetrics for the session, routes CLI args to the correct fetch strategy,
builds odds tables, optionally runs web search and LLM pipeline, and writes output.

Never raises — all exceptions are caught, logged to metrics.errors, and the
function returns exit code 1 on any unrecoverable error.
"""

from __future__ import annotations

import datetime

from kalshi_sports_edge.cli import CLIArgs
from kalshi_sports_edge.models import MarketData, OddsTable, ReportData, RunMetrics
from kalshi_sports_edge.output import pdf_report, terminal
from kalshi_sports_edge.services import (
    deep_research,
    llm_pipeline,
    market_fetcher,
    odds_engine,
    web_search,
)
from kalshi_sports_edge.services.llm_pipeline import (
    AnthropicClientWrapper,
    OpenAIClientWrapper,
)


def run(args: CLIArgs) -> int:
    """Main application entry point. Returns 0 on success, 1 on error."""
    metrics = RunMetrics(started_at=datetime.datetime.now())

    # Build LLM client up-front so we fail fast on missing API key
    llm_client: OpenAIClientWrapper | AnthropicClientWrapper | None = None
    if args.llm:
        try:
            llm_client = llm_pipeline.get_llm_client(args.provider)
        except ValueError as exc:
            terminal.console.print(f"[red]Error: {exc}[/red]")
            return 1

    # --- Fetch markets ---
    try:
        markets = _resolve_markets(args, metrics)
    except Exception as exc:
        terminal.console.print(f"[red]Failed to fetch markets: {exc}[/red]")
        metrics.errors.append(str(exc))
        metrics.finished_at = datetime.datetime.now()
        terminal.print_run_summary(metrics)
        return 1

    if not markets:
        if args.date:
            terminal.console.print(
                f"[yellow]No sports markets found with game date {args.date}.[/yellow]"
            )
            hints = market_fetcher.get_available_game_dates(sports=args.sports)
            if hints:
                terminal.console.print(
                    f"[dim]Available game dates: {', '.join(hints)}[/dim]"
                )
        else:
            terminal.console.print(
                "[yellow]No sports markets found matching your filters.[/yellow]"
            )
        metrics.finished_at = datetime.datetime.now()
        terminal.print_run_summary(metrics)
        return 0

    metrics.markets_fetched = len(markets)

    # --- Filter out games that have already started ---
    if args.exclude_started:
        started_count = sum(1 for m in markets if m.has_started())
        if started_count > 0:
            markets = [m for m in markets if not m.has_started()]
            terminal.console.print(
                f"[dim]Excluded {started_count} market(s) that have already started.[/dim]"
            )

    metrics.markets_after_filter = len(markets)

    # Check if all markets were filtered out
    if not markets:
        terminal.console.print(
            "[yellow]No upcoming markets to display after filtering started games.[/yellow]"
        )
        metrics.finished_at = datetime.datetime.now()
        terminal.print_run_summary(metrics)
        return 0

    # --- Quick summary view (sorted by volume, no detailed analysis) ---
    if args.summary:
        from kalshi_sports_edge.services.market_utils import group_markets_by_game
        terminal.print_volume_summary(markets)
        games = group_markets_by_game(markets)
        metrics.games_analyzed = len(games)
        metrics.finished_at = datetime.datetime.now()
        terminal.print_run_summary(metrics)
        return 0

    # --- Build odds tables (skip markets with no price data) ---
    valid_markets: list[MarketData] = []
    odds_tables: list[OddsTable] = []
    skipped = 0
    for m in markets:
        try:
            odds_tables.append(odds_engine.calc_market_odds(m))
            valid_markets.append(m)
        except ValueError:
            skipped += 1
            metrics.errors.append(f"No price data for {m.ticker} — skipped")

    if skipped:
        terminal.console.print(
            f"[dim]Skipped {skipped} market(s) with no bid/ask/last price data.[/dim]"
        )

    if not odds_tables:
        terminal.console.print("[yellow]No markets have valid price data.[/yellow]")
        metrics.finished_at = datetime.datetime.now()
        terminal.print_run_summary(metrics)
        return 0

    # --- Optional web search (one query for the batch) ---
    web_ctx: str | None = None
    if args.web_search:
        anchor = (
            valid_markets[0].title
            if len(valid_markets) == 1
            else f"US sports prediction markets {datetime.date.today()}"
        )
        general = web_search.search_general(anchor)
        social = web_search.search_social(anchor)
        web_ctx = web_search.build_context_string(anchor, general + social)
        metrics.web_searches_made = 2 if web_ctx else 0

    # --- Deep research path ---
    if args.deep_research and llm_client is not None:
        exit_code = _run_deep_research(
            valid_markets, odds_tables, llm_client, args, web_ctx, metrics
        )
        metrics.finished_at = datetime.datetime.now()
        terminal.print_run_summary(metrics)
        return exit_code

    # --- Single-pass (or odds-only) path ---
    event_groups = _group_by_event(valid_markets, odds_tables)
    for group_markets, group_tables in event_groups:
        group_reports: list[ReportData] = []
        try:
            for m, t in zip(group_markets, group_tables):
                if args.llm and llm_client is not None:
                    report = llm_pipeline.run_single_pass(
                        market=m,
                        odds_table=t,
                        client=llm_client,
                        model=args.model,
                        web_context=web_ctx,
                        edge_threshold=args.edge_threshold,
                    )
                    metrics.llm_calls_made += 1
                else:
                    report = ReportData(market=m, odds_table=t)
                group_reports.append(report)

            terminal.print_event_group(
                group_markets, group_tables, group_reports, args.verbose
            )

            if args.pdf:
                for report in group_reports:
                    path = pdf_report.write_single_report(report)
                    terminal.console.print(f"[green]PDF saved → {path}[/green]")

        except llm_pipeline.AuthenticationError as exc:
            terminal.console.print(f"[red]Authentication Error: {exc}[/red]")
            metrics.errors.append(str(exc))
            return 1
        except Exception as exc:
            for m in group_markets:
                terminal.console.print(f"[red]Error processing {m.ticker}: {exc}[/red]")
                metrics.errors.append(f"{m.ticker}: {exc}")

    metrics.finished_at = datetime.datetime.now()
    terminal.print_run_summary(metrics)
    return 0


def _run_deep_research(
    markets: list[MarketData],
    odds_tables: list[OddsTable],
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    args: CLIArgs,
    web_ctx: str | None,
    metrics: RunMetrics,
) -> int:
    """Run enhanced deep research with multi-source web search and comprehensive metrics."""
    terminal.console.print(
        f"\n[bold cyan]Running Enhanced Deep Research Pipeline "
        f"({len(markets)} market{'s' if len(markets) != 1 else ''})...[/bold cyan]"
    )
    terminal.console.print(
        "[dim]Stages: [1] Multi-source web search → [2] Probability estimation → "
        "[3] Edge/EV/ROI calculation → [4] Classification → [5] Consolidation[/dim]"
    )
    
    try:
        # Run enhanced deep research with progress updates
        def progress(msg: str) -> None:
            terminal.console.print(f"[dim]{msg}[/dim]")
        
        report = deep_research.run_deep_research(
            markets=markets,
            odds_tables=odds_tables,
            client=client,
            model=args.model,
            web_context=web_ctx,
            progress=progress,
        )
        report.metrics = metrics
        
        # Estimate LLM calls: 1 per market for probability estimation
        metrics.llm_calls_made = len(markets)
        metrics.web_searches_made = len(set(m.event_ticker for m in markets)) * 5  # 5 sources per game
        
        # Get analyses for enhanced output
        analyses = getattr(report, '_analyses', [])
        
        # Use enhanced output format
        if analyses:
            terminal.print_enhanced_consolidated_report(
                analyses=analyses,
                generated_at=report.generated_at,
                model=args.model,
                verbose=args.verbose,
            )
        else:
            # Fallback to old format
            terminal.print_consolidated_report(report, verbose=args.verbose)

        if args.pdf:
            path = pdf_report.write_consolidated_report(report)
            terminal.console.print(f"\n[green]PDF saved → {path}[/green]")

        return 0

    except llm_pipeline.AuthenticationError as exc:
        terminal.console.print(f"[red]Authentication Error: {exc}[/red]")
        metrics.errors.append(str(exc))
        return 1
    except Exception as exc:
        terminal.console.print(f"[red]Deep research failed: {exc}[/red]")
        metrics.errors.append(str(exc))
        return 1


def _group_by_event(
    markets: list[MarketData],
    tables: list[OddsTable],
) -> list[tuple[list[MarketData], list[OddsTable]]]:
    """Group parallel markets and tables by event_ticker, preserving first-seen order.

    Markets for the same game (same event_ticker) are collected into one group
    so they can be displayed as a single combined block.
    """
    seen: dict[str, int] = {}
    groups: list[tuple[list[MarketData], list[OddsTable]]] = []
    for m, t in zip(markets, tables):
        key = m.event_ticker
        if key not in seen:
            seen[key] = len(groups)
            groups.append(([], []))
        idx = seen[key]
        groups[idx][0].append(m)
        groups[idx][1].append(t)
    return groups


def _resolve_markets(args: CLIArgs, metrics: RunMetrics) -> list[MarketData]:
    """Route to the appropriate fetch function based on CLI args."""
    if args.ticker:
        return [market_fetcher.fetch_by_ticker(args.ticker)]

    if args.search:
        return market_fetcher.fetch_by_keyword(
            args.search, args.limit, args.min_volume, args.min_open_interest,
            sports=args.sports,
        )

    if args.date:
        terminal.console.print(
            "[dim]Note: --date filters by game date (parsed from ticker), "
            "not market settlement date. This may take a moment.[/dim]"
        )
        return market_fetcher.fetch_by_date(
            args.date, args.limit, args.min_volume, args.min_open_interest,
            sports=args.sports,
        )

    # --pick N or default (pick was set to limit in _validate_args)
    n = args.pick or args.limit
    return market_fetcher.fetch_top_n(n, args.min_volume, args.min_open_interest, sports=args.sports)
