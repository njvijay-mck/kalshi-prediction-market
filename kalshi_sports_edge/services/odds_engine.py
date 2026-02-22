"""Pure odds math for Kalshi binary markets.

Key binary constraint: yes_price + no_price = 100 (always).
This is enforced in calc_market_odds() — no_price is always derived
from yes_price, never read independently from the API.

Overround semantics on a binary Kalshi market:
  - Using mid-price: overround ≈ 0.0 (math identity for binary markets)
  - Using bid/ask:   overround = (ask - bid) / 100  (the bid/ask spread = market vig)
"""

from __future__ import annotations

import math

from kalshi_sports_edge.config import WIDE_SPREAD_THRESHOLD
from kalshi_sports_edge.models import MarketData, OddsRow, OddsTable


def calc_market_odds(market: MarketData, price_source: str = "mid") -> OddsTable:
    """Build a complete OddsTable for a binary Kalshi market.

    Enforces the binary constraint: no_price = 100 - yes_price.
    Raises ValueError if no price data is available at all.
    """
    yes_price, source_used, wide_spread = _resolve_yes_price(market, price_source)
    no_price = 100 - yes_price

    yes_row = _build_odds_row("YES", yes_price)
    no_row = _build_odds_row("NO", no_price)
    overround = yes_row.implied_prob + no_row.implied_prob - 1.0

    return OddsTable(
        market=market,
        yes_row=yes_row,
        no_row=no_row,
        overround=overround,
        price_source=source_used,
        wide_spread=wide_spread,
    )


def calc_edge(true_prob: float, market_implied: float) -> float:
    """Edge = true_prob - market_implied.

    Positive edge means the market underprices this outcome.
    Negative edge means the market overprices it.
    """
    return true_prob - market_implied


def calc_ev(edge: float, price_cents: int) -> float:
    """Expected value per $1 wagered.

    EV = edge / implied_prob
    A positive EV means this is a +EV bet at the current market price.
    """
    implied = price_cents / 100.0
    if implied <= 0:
        return 0.0
    return edge / implied


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_yes_price(
    market: MarketData, source: str
) -> tuple[int, str, bool]:
    """Resolve the YES price in cents using the requested source.

    Returns (yes_price_cents, source_actually_used, wide_spread_flag).

    Fallback chain: mid → last_price → yes_ask → yes_bid
    wide_spread_flag is True when bid/ask spread exceeds WIDE_SPREAD_THRESHOLD.
    Raises ValueError if no price data is available at all.
    """
    # Treat 0 as absent — Kalshi valid prices are 1-99 cents
    def valid(p: int | None) -> int | None:
        return p if p and 1 <= p <= 99 else None

    wide_spread = False
    bid = valid(market.yes_bid)
    ask = valid(market.yes_ask)
    last = valid(market.last_price)

    if source == "mid" and bid is not None and ask is not None:
        spread = ask - bid
        wide_spread = spread > WIDE_SPREAD_THRESHOLD
        return (bid + ask) // 2, "mid", wide_spread

    # Fallbacks (also used when bid or ask is null/zero)
    if last is not None:
        return last, "last", False
    if ask is not None:
        return ask, "ask", False
    if bid is not None:
        return bid, "bid", False

    raise ValueError(f"No valid price data (1-99¢) for market {market.ticker}")


def _build_odds_row(outcome: str, price_cents: int) -> OddsRow:
    """Compute all odds formats for one side of a binary market."""
    implied = price_cents / 100.0
    decimal = 100.0 / price_cents
    american = _to_american(price_cents)
    fractional = _to_fractional(price_cents)
    return OddsRow(
        outcome=outcome,
        price_cents=price_cents,
        implied_prob=implied,
        decimal_odds=round(decimal, 3),
        american_odds=american,
        fractional_str=fractional,
    )


def _to_american(price_cents: int) -> int:
    """Convert a cent price to American moneyline format.

    Favorite (implied > 50%): american = -round(prob / (1 - prob) * 100)
    Underdog (implied < 50%): american = +round((1 - prob) / prob * 100)
    Pick-em (50¢): -100 by convention.
    """
    prob = price_cents / 100.0
    if prob >= 0.5:
        return -round(prob / (1.0 - prob) * 100)
    return round((1.0 - prob) / prob * 100)


def _to_fractional(price_cents: int) -> str:
    """Convert a cent price to simplified fractional odds string (N/D).

    Fractional odds = (1 / implied_prob) - 1 = (100 - price) / price.
    Simplified using GCD.
    """
    numerator = 100 - price_cents
    denominator = price_cents
    if numerator == 0:
        return "0/1"
    gcd = math.gcd(numerator, denominator)
    return f"{numerator // gcd}/{denominator // gcd}"
