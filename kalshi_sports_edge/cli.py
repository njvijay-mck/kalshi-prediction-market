"""CLI argument parsing and validation for kalshi_sports_edge.

Market source flags are mutually exclusive (argparse enforces this).
If none are given, defaults to top-N sports markets by volume (--pick = --limit).

Usage examples:
    uv run python -m kalshi_sports_edge NFLCH-25NOV17
    uv run python -m kalshi_sports_edge --search "Bears" --llm --web-search
    uv run python -m kalshi_sports_edge --pick 5 --min-volume 500 --deep-research --pdf
    uv run python -m kalshi_sports_edge --date 2026-03-01 --limit 10 --llm --provider kimi
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from dataclasses import dataclass

from kalshi_sports_edge.config import (
    DEFAULT_LIMIT,
    DEFAULT_MIN_OI,
    DEFAULT_MIN_VOLUME,
    EDGE_THRESHOLD_DEFAULT,
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_ENV_KEYS,
    SUPPORTED_SPORTS,
)


@dataclass
class CLIArgs:
    # Market source (exactly one will be set after validation)
    ticker: str | None
    search: str | None
    date: datetime.date | None
    pick: int | None

    # Filtering
    limit: int
    min_volume: int
    min_open_interest: int
    exclude_started: bool  # Filter out games that have already started
    sports: list[str] | None  # Filter by specific sports (e.g., ['soccer', 'tennis'])

    # LLM
    llm: bool
    provider: str
    model: str
    deep_research: bool

    # Web search
    web_search: bool

    # Output
    edge_threshold: float
    pdf: bool   # Save per-market PDF reports
    html: bool  # Save consolidated HTML report
    verbose: bool
    summary: bool  # Quick summary view sorted by volume


def parse_args(argv: list[str] | None = None) -> CLIArgs:
    parser = argparse.ArgumentParser(
        prog="kalshi-sports-edge",
        description="Kalshi US Sports Prediction Market Odds Calculator & Edge Finder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s NFLCH-25NOV17                           # single market by ticker
  %(prog)s --search "Bears" --llm                   # search + LLM single-pass
  %(prog)s --pick 5 --min-volume 500 --deep-research # top-5 with deep research
  %(prog)s --date 2026-03-01 --llm --pdf            # markets closing on date
  %(prog)s --pick 10 --provider kimi --llm          # use Kimi Code
  %(prog)s --pick 10 --provider moonshot --llm      # use Moonshot AI (kimi-k2-5)
  %(prog)s --pick 20 --summary                      # quick summary, sorted by volume
  %(prog)s --search "NBA" --no-exclude-started      # include already-started games
        """,
    )

    # Market source (mutually exclusive)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "ticker", nargs="?", metavar="TICKER",
        help="Exact Kalshi market ticker (e.g. NFLCH-25NOV17)",
    )
    source.add_argument(
        "--search", metavar="QUERY",
        help="Search open sports markets by keyword (client-side title/ticker match)",
    )
    source.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Find sports markets with game date on this date (client-side scan — may be slow)",
    )
    source.add_argument(
        "--pick", type=int, metavar="N",
        help="Top N sports markets by volume (default when no other source given)",
    )

    # Filtering
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT, metavar="N",
        help=f"Max markets to display (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--min-volume", type=int, default=DEFAULT_MIN_VOLUME,
        dest="min_volume", metavar="N",
        help="Minimum volume in contracts (default: 0)",
    )
    parser.add_argument(
        "--min-open-interest", type=int, default=DEFAULT_MIN_OI,
        dest="min_open_interest", metavar="N",
        help="Minimum open interest in contracts (default: 0)",
    )
    parser.add_argument(
        "--exclude-started", action=argparse.BooleanOptionalAction,
        default=True, dest="exclude_started",
        help="Exclude games that have already started (default: True)",
    )
    parser.add_argument(
        "--sports", metavar="SPORT",
        nargs="+", choices=SUPPORTED_SPORTS,
        help=f"Filter by specific sports. Choices: {', '.join(SUPPORTED_SPORTS)}",
    )

    # LLM
    parser.add_argument(
        "--llm", action="store_true",
        help="Run LLM single-pass analysis (requires provider API key env var)",
    )
    parser.add_argument(
        "--provider", choices=["claude", "kimi", "moonshot"], default="claude",
        help="LLM provider: claude (Anthropic), kimi (Kimi Code), or moonshot (Moonshot AI) — default: claude",  # noqa: E501
    )
    parser.add_argument(
        "--model", metavar="MODEL",
        help="Override the default model for the selected provider",
    )
    parser.add_argument(
        "--deep-research", action="store_true", dest="deep_research",
        help="Run 4-stage deep research pipeline across all fetched markets (implies --llm)",
    )

    # Web search
    parser.add_argument(
        "--web-search", action="store_true", dest="web_search",
        help="Fetch web context via Brave Search before LLM analysis (requires BRAVE_SEARCH_API_KEY)",  # noqa: E501
    )

    # Output
    parser.add_argument(
        "--edge-threshold", type=float, default=EDGE_THRESHOLD_DEFAULT,
        dest="edge_threshold", metavar="FLOAT",
        help=f"Minimum edge (0-1) for RECOMMENDED POSITION banner (default: {EDGE_THRESHOLD_DEFAULT})",  # noqa: E501
    )
    parser.add_argument(
        "--pdf", action="store_true",
        help="Save per-market PDF report to reports/YYYY-MM-DD/ directory",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Save consolidated single-page HTML report to reports/YYYY-MM-DD/ directory",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print web context and deep-research stage transcripts",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Show quick summary table sorted by volume (no detailed analysis)",
    )

    ns = parser.parse_args(argv)

    # Coerce deep_research → llm=True
    use_llm = ns.llm or ns.deep_research

    args = CLIArgs(
        ticker=ns.ticker,
        search=ns.search,
        date=_parse_date(ns.date) if ns.date else None,
        pick=ns.pick,
        limit=ns.limit,
        min_volume=ns.min_volume,
        min_open_interest=ns.min_open_interest,
        exclude_started=ns.exclude_started,
        sports=ns.sports,
        llm=use_llm,
        provider=ns.provider,
        model=ns.model or PROVIDER_DEFAULT_MODELS[ns.provider],
        deep_research=ns.deep_research,
        web_search=ns.web_search,
        edge_threshold=ns.edge_threshold,
        pdf=ns.pdf,
        html=ns.html,
        verbose=ns.verbose,
        summary=ns.summary,
    )

    _validate_args(args)
    return args


def _parse_date(s: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        print(f"Error: --date must be YYYY-MM-DD, got '{s}'", file=sys.stderr)
        sys.exit(1)


def _validate_args(args: CLIArgs) -> None:
    # LLM API key check
    if args.llm:
        env_key = PROVIDER_ENV_KEYS[args.provider]
        if not os.environ.get(env_key):
            print(
                f"Error: --llm with --provider {args.provider} requires env var '{env_key}'. "
                f"Add it to your .env file.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Web search without API key is non-fatal (warned in web_search module)
    if args.web_search and not os.environ.get("BRAVE_SEARCH_API_KEY"):
        print(
            "Warning: --web-search has no effect without BRAVE_SEARCH_API_KEY set.",
            file=sys.stderr,
        )

    # Edge threshold range
    if not (0.0 < args.edge_threshold < 1.0):
        print("Error: --edge-threshold must be between 0 and 1 exclusive.", file=sys.stderr)
        sys.exit(1)

    # Default: if no source provided, use --pick = --limit
    if not any([args.ticker, args.search, args.date, args.pick]):
        args.pick = args.limit
