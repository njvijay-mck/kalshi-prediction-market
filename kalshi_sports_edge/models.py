"""Data model dataclasses for kalshi_sports_edge.

All prices are in cents (integers 1-99) unless noted.
Volume and open_interest are in contracts (integers).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

# NBA tip-off is typically 3 hours before the market's expected_expiration_time.
# This offset is used as a fallback for all sports series since Kalshi does not
# expose a game start time field.
_GAME_START_OFFSET = datetime.timedelta(hours=3)
_UTC = datetime.timezone.utc


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
    yes_team: str | None = None                     # team name for YES outcome
    no_team: str | None = None                      # team name for NO outcome

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

    @property
    def no_price(self) -> int | None:
        """NO price = 100 - YES price (using mid). None if no price data."""
        mid = self.mid_price
        return 100 - mid if mid is not None else None

    def game_start_time(self) -> datetime.datetime | None:
        """Estimate game start time from expected_expiration_time.

        Returns UTC datetime by subtracting _GAME_START_OFFSET from
        expected_expiration_time. Returns None if no expiration time.
        """
        if not self.expected_expiration_time:
            return None
        try:
            dt = datetime.datetime.fromisoformat(
                self.expected_expiration_time.replace("Z", "+00:00")
            )
            return dt - _GAME_START_OFFSET
        except (ValueError, AttributeError):
            return None

    def has_started(self) -> bool:
        """Return True if the game has already started (based on current UTC time)."""
        start_time = self.game_start_time()
        if start_time is None:
            return False
        return datetime.datetime.now(_UTC) >= start_time


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
    """

    market: MarketData
    yes_row: OddsRow
    no_row: OddsRow
    overround: float    # (yes_implied + no_implied) - 1.0
    price_source: str   # "mid" | "last" | "ask" | "bid"
    wide_spread: bool   # True when bid/ask spread exceeds threshold


@dataclass
class GameGroup:
    """A group of markets for the same game (both sides of a binary market).

    For a game like Spurs vs Pistons:
    - event_ticker: KXNBAGAME-26FEB23SASDET
    - team_a_market: MarketData for SAS YES (ticker: ...-SAS)
    - team_b_market: MarketData for DET YES (ticker: ...-DET)
    """

    event_ticker: str
    game_date: datetime.date | None
    expected_expiration_time: str | None
    team_a_name: str
    team_a_abbrev: str
    team_a_market: MarketData
    team_b_name: str
    team_b_abbrev: str
    team_b_market: MarketData

    @property
    def combined_volume(self) -> int:
        """Total volume across both sides."""
        return self.team_a_market.volume + self.team_b_market.volume

    @property
    def combined_oi(self) -> int:
        """Total open interest across both sides."""
        return self.team_a_market.open_interest + self.team_b_market.open_interest

    @property
    def matchup_str(self) -> str:
        """Formatted matchup like 'San Antonio vs Detroit'."""
        return f"{self.team_a_name} vs {self.team_b_name}"

    def game_start_time(self) -> datetime.datetime | None:
        """Game start time from either market."""
        return self.team_a_market.game_start_time()

    def has_started(self) -> bool:
        """True if game has started (based on team_a market)."""
        return self.team_a_market.has_started()

    def get_price_display(self, side: str) -> str:
        """Get YES-NO price display for a side.

        side: 'a' for team_a, 'b' for team_b
        Returns: '45-55' meaning YES 45¢ / NO 55¢
        """
        if side == 'a':
            market = self.team_a_market
        elif side == 'b':
            market = self.team_b_market
        else:
            return "—"

        yes = market.mid_price
        if yes is None:
            return "—"
        no = 100 - yes
        return f"{yes}-{no}"


@dataclass
class RunMetrics:
    """Performance and metadata for one CLI invocation."""

    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None
    markets_fetched: int = 0
    markets_after_filter: int = 0
    games_analyzed: int = 0  # Number of unique games (after grouping sides)
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


@dataclass
class MarketAnalysis:
    """Comprehensive analysis for a single market including LLM probabilities and metrics."""
    
    market: MarketData
    odds_table: OddsTable
    
    # LLM-estimated true probabilities (0-1)
    llm_yes_prob: float
    llm_no_prob: float
    
    # Calculated metrics
    yes_edge: float  # llm_yes - market_yes_implied
    no_edge: float   # llm_no - market_no_implied
    yes_ev: float    # Expected value per cent for YES
    no_ev: float     # Expected value per cent for NO
    yes_roi: float   # Return on investment % for YES
    no_roi: float    # Return on investment % for NO
    
    # Best side (highest edge)
    best_edge: float
    best_ev: float
    best_side: str  # "YES" or "NO"
    best_roi: float
    
    # Classification
    sentiment: str  # "Bullish", "Neutral", "Bearish"
    confidence: str  # "High", "Medium", "Low"
    reason: str  # "stats", "injury", "form", "news", "data", "record", "consensus", "volume", "schedule", "weather", "momentum", "unclear"
    
    # Context and analysis
    web_context: str
    llm_analysis: str
    
    @property
    def market_yes_implied(self) -> float:
        """Market implied probability for YES."""
        return self.odds_table.yes_row.implied_prob
    
    @property
    def market_no_implied(self) -> float:
        """Market implied probability for NO."""
        return self.odds_table.no_row.implied_prob
    
    def to_summary_row(self) -> dict:
        """Convert to summary table row format."""
        return {
            "market": self.market.title,
            "best_edge": self.best_edge,
            "best_ev": self.best_ev,
            "sentiment": self.sentiment,
            "roi": self.best_roi,
            "rec": "BUY" if self.best_edge >= 0.05 else ("SELL" if self.best_edge <= -0.05 else "HOLD"),
            "confidence": self.confidence,
            "reason": self.reason,
            "volume": self.market.volume,
            "oi": self.market.open_interest,
        }
