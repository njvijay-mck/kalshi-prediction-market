"""Data model dataclasses for kalshi_sports_edge.

All prices are in cents (integers 1-99) unless noted.
Volume and open_interest are in contracts (integers).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class MarketData:
    """Normalized representation of a single Kalshi binary sports market."""

    ticker: str
    title: str
    event_ticker: str
    category: str | None
    tags: list[str]
    status: str
    yes_bid: int | None    # cents 1-99, null when no resting orders
    yes_ask: int | None    # cents 1-99, null when no resting orders
    last_price: int | None  # cents, last traded price
    volume: int               # contracts traded
    open_interest: int        # open contracts
    close_time: str | None  # ISO8601 string — settlement deadline, NOT game date
    game_date: datetime.date | None = None          # game date, parsed from event_ticker
    expected_expiration_time: str | None = None  # ISO8601, proxy for game end time
    yes_team: str | None = None                     # team name for YES outcome (e.g. "Minnesota")
    no_team: str | None = None                      # team name for NO outcome (e.g. "Philadelphia")

    @property
    def mid_price(self) -> int | None:
        """Integer midpoint of yes bid/ask. None if either side absent."""
        if self.yes_bid is not None and self.yes_ask is not None:
            return (self.yes_bid + self.yes_ask) // 2
        return self.yes_bid if self.yes_bid is not None else self.yes_ask

    @property
    def spread_cents(self) -> int | None:
        """Bid/ask spread in cents. None if either side absent."""
        if self.yes_bid is not None and self.yes_ask is not None:
            return self.yes_ask - self.yes_bid
        return None


@dataclass
class OddsRow:
    """One row of the odds table — YES or NO side of a binary market."""

    outcome: str            # "YES" or "NO"
    price_cents: int        # 1-99
    implied_prob: float     # price_cents / 100.0
    decimal_odds: float     # 100.0 / price_cents
    american_odds: int      # moneyline integer (+/-)
    fractional_str: str     # e.g. "4/1" or "1/4"
    edge: float | None = None  # filled after LLM analysis


@dataclass
class OddsTable:
    """Complete odds analysis for one Kalshi binary market.

    Binary constraint: no_price = 100 - yes_price always.
    Overround using mid-price is ~0 for efficient markets.
    Overround using bid/ask reflects the spread as market-maker vig.
    """

    market: MarketData
    yes_row: OddsRow
    no_row: OddsRow
    overround: float    # (yes_implied + no_implied) - 1.0
    price_source: str   # "mid" | "last" | "ask" | "bid"
    wide_spread: bool   # True when bid/ask spread exceeds WIDE_SPREAD_THRESHOLD


@dataclass
class RunMetrics:
    """Performance and metadata for one CLI invocation."""

    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None
    markets_fetched: int = 0
    markets_after_filter: int = 0
    llm_calls_made: int = 0
    web_searches_made: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def elapsed_seconds(self) -> float | None:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class ReportData:
    """Data for a single-market analysis report."""

    market: MarketData
    odds_table: OddsTable
    llm_analysis: str | None = None
    recommended_side: str | None = None   # "YES", "NO", or None
    recommended_edge: float | None = None
    web_context: str | None = None
    edge_threshold_used: float = 0.05


@dataclass
class ConsolidatedReport:
    """Multi-market deep research report produced by the 4-stage pipeline."""

    generated_at: datetime.datetime
    markets: list[MarketData]
    odds_tables: list[OddsTable]
    research_output: str | None = None
    critique_output: str | None = None
    rebuttal_output: str | None = None
    consolidation_output: str | None = None
    metrics: RunMetrics | None = None
