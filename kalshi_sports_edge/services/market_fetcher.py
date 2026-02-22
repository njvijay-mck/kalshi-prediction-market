"""Kalshi market fetching for US sports binary markets.

Key discovery: the flat /markets?status=open endpoint returns
KXMVESPORTSMULTIGAMEEXTENDED parlay markets first (thousands of them),
burying the individual game matchup markets (KXNBAGAME, KXNFLGAME, etc.)
deep in the result set.

Correct approach: use /events?series_ticker=<series>&status=open for each
known sports game series. This returns individual matchup events with their
embedded markets directly (category=Sports at event level, even though
individual market dicts have category=None).

All raw dict access uses .get() with explicit defaults — both demo and prod
return null for category/tags/risk_limit_cents fields on market objects.
"""

from __future__ import annotations

import datetime
import re
import time

from auth.client import raw_get
from kalshi_sports_edge.config import (
    MAX_PAGE_SIZE,
    RATE_LIMIT_SLEEP_S,
    SPORTS_CATEGORY,
    SPORTS_TICKER_PREFIXES,
    US_SPORTS_GAME_SERIES,
)
from kalshi_sports_edge.models import MarketData


def fetch_by_ticker(ticker: str) -> MarketData:
    """Fetch a single market by exact Kalshi ticker.

    Makes an extra /events call to get the event title for team label derivation.
    Raises ValueError if the ticker is not found or returns no data.
    """
    data = raw_get(f"/markets/{ticker}")
    m = data.get("market", data)
    if not m or not m.get("ticker"):
        raise ValueError(f"Market not found: {ticker}")
    event_ticker = m.get("event_ticker", "")
    event_title = _fetch_event_title(event_ticker)
    return _parse_market_dict(m, event_title=event_title)


def fetch_by_keyword(
    query: str,
    limit: int = 10,
    min_volume: int = 0,
    min_open_interest: int = 0,
) -> list[MarketData]:
    """Search open sports game markets whose title or ticker contains query.

    Fetches from sports game series (not the flat /markets endpoint).
    Filtering is client-side — Kalshi has no server-side text search.
    """
    markets = _fetch_via_sports_series(target=max(limit * 10, 200))
    query_lower = query.lower()
    matched = [
        m for m in markets
        if query_lower in m.title.lower()
        or query_lower in m.ticker.lower()
        or query_lower in m.event_ticker.lower()
    ]
    return _apply_filters(matched, min_volume, min_open_interest)[:limit]


def fetch_by_date(
    game_date: datetime.date,
    limit: int = 50,
    min_volume: int = 0,
    min_open_interest: int = 0,
) -> list[MarketData]:
    """Fetch open sports markets whose game date matches game_date.

    Filters by game_date (parsed from event_ticker), not market close/settlement time.
    Fetches from sports game series. No server-side date filter exists.
    """
    markets = _fetch_via_sports_series(target=max(limit * 10, 300))
    on_date = [m for m in markets if m.game_date == game_date]
    return _apply_filters(on_date, min_volume, min_open_interest)[:limit]


def fetch_top_n(
    n: int,
    min_volume: int = 0,
    min_open_interest: int = 0,
) -> list[MarketData]:
    """Fetch top N open sports markets sorted by volume descending."""
    markets = _fetch_via_sports_series(target=n * 10)
    filtered = _apply_filters(markets, min_volume, min_open_interest)
    return sorted(filtered, key=lambda m: m.volume, reverse=True)[:n]


def is_sports_market(market: MarketData) -> bool:
    """Return True if this is an individual US sports game market.

    Checks event_ticker prefix (KXNBAGAME, KXNFLGAME, etc.) first,
    then falls back to category field. The prefix check is the most
    reliable since individual game market dicts have category=None in prod.
    """
    event_upper = market.event_ticker.upper()
    if any(event_upper.startswith(p) for p in SPORTS_TICKER_PREFIXES):
        return True
    return market.category == SPORTS_CATEGORY


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _fetch_via_sports_series(target: int) -> list[MarketData]:
    """Fetch individual game markets by iterating known sports event series.

    For each series in US_SPORTS_GAME_SERIES:
      GET /events?series_ticker=<series>&status=open&with_nested_markets=true
    Markets embedded in each event are extracted and deduplicated by ticker.

    Stops when target market count is reached or all series are exhausted.
    """
    seen: set[str] = set()
    results: list[MarketData] = []

    for series_ticker in US_SPORTS_GAME_SERIES:
        if len(results) >= target:
            break

        cursor: str | None = None
        while len(results) < target:
            params: dict[str, object] = {
                "status": "open",
                "series_ticker": series_ticker,
                "limit": min(50, target),
                "with_nested_markets": "true",
            }
            if cursor:
                params["cursor"] = cursor

            data = raw_get("/events", **params)
            events = data.get("events", [])
            if not events:
                break

            for event in events:
                event_title = event.get("title", "")
                for m_raw in event.get("markets", []):
                    ticker = m_raw.get("ticker", "")
                    # Markets embedded in events use status='active' (not 'open')
                    status = m_raw.get("status", "")
                    if ticker and ticker not in seen and status in ("open", "active"):
                        seen.add(ticker)
                        results.append(_parse_market_dict(m_raw, event_title=event_title))

            cursor = data.get("cursor") or None
            if not cursor:
                break
            time.sleep(RATE_LIMIT_SLEEP_S)

    return results


def _paginate_markets(status: str = "open", target: int = 200) -> list[MarketData]:
    """Cursor-paginated fetch from the flat /markets endpoint.

    Used only for fetch_by_ticker fallback.
    Note: this endpoint returns KXMVESPORTSMULTIGAMEEXTENDED parlay markets
    first. Use _fetch_via_sports_series() for sports game discovery.
    """
    results: list[MarketData] = []
    cursor: str | None = None

    while len(results) < target:
        page_size = min(MAX_PAGE_SIZE, target - len(results))
        params: dict[str, object] = {"status": status, "limit": page_size}
        if cursor:
            params["cursor"] = cursor

        data = raw_get("/markets", **params)
        batch = data.get("markets", [])
        if not batch:
            break

        results.extend(_parse_market_dict(m) for m in batch)

        cursor = data.get("cursor") or None
        if not cursor:
            break
        time.sleep(RATE_LIMIT_SLEEP_S)

    return results


_MONTH_MAP: dict[str, int] = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

_GAME_DATE_RE = re.compile(r"^(\d{2})([A-Z]{3})(\d{2})")


def _fetch_event_title(event_ticker: str) -> str:
    """Fetch the event title for a given event_ticker (e.g. 'Philadelphia at Minnesota').

    Used by fetch_by_ticker to get team names when event context is unavailable.
    Returns empty string on any error.
    """
    if not event_ticker:
        return ""
    try:
        data = raw_get(f"/events/{event_ticker}")
        event = data.get("event", data)
        return event.get("title", "") or ""
    except Exception:
        return ""


def _derive_opponent(event_title: str, yes_team: str) -> str | None:
    """Derive the opposing team name from event title 'TeamA at TeamB'.

    Given yes_team ('Minnesota') and event_title ('Philadelphia at Minnesota'),
    returns 'Philadelphia'. Returns None if parsing fails or no match.
    """
    parts = [p.strip() for p in event_title.split(" at ", 1)]
    if len(parts) != 2:
        return None
    team_a, team_b = parts
    yes_lower = yes_team.lower()
    if yes_lower == team_b.lower():
        return team_a
    if yes_lower == team_a.lower():
        return team_b
    return None


def _parse_game_date(event_ticker: str) -> datetime.date | None:
    """Extract game date from event_ticker like 'KXNBAGAME-26FEB22CLEOKC'.

    Kalshi encodes the game date as YYMONDD in the second dash-separated segment.
    Returns None if the ticker doesn't match the expected pattern.
    """
    parts = event_ticker.split("-")
    if len(parts) < 2:
        return None
    m = _GAME_DATE_RE.match(parts[1])
    if not m:
        return None
    yy, mon, dd = m.group(1), m.group(2), m.group(3)
    month = _MONTH_MAP.get(mon)
    if not month:
        return None
    try:
        return datetime.date(2000 + int(yy), month, int(dd))
    except ValueError:
        return None


def _parse_market_dict(m: dict, event_title: str = "") -> MarketData:
    """Convert a raw API market dict to MarketData.

    Uses .get() with explicit defaults for every field — the API returns
    null for many fields. Volume fallback: try "volume" then "volume_24h".
    game_date is parsed from event_ticker (YYMONDD segment).
    yes_team comes from yes_sub_title; no_team is derived from event_title.
    """
    tags_raw = m.get("tags") or []
    event_ticker = m.get("event_ticker", "")
    yes_team = m.get("yes_sub_title") or None
    no_team = _derive_opponent(event_title, yes_team) if yes_team and event_title else None
    return MarketData(
        ticker=m.get("ticker", ""),
        title=m.get("title", ""),
        event_ticker=event_ticker,
        category=m.get("category"),
        tags=tags_raw if isinstance(tags_raw, list) else [],
        status=m.get("status", ""),
        yes_bid=m.get("yes_bid"),
        yes_ask=m.get("yes_ask"),
        last_price=m.get("last_price"),
        volume=int(m.get("volume") or m.get("volume_24h") or 0),
        open_interest=int(m.get("open_interest") or 0),
        close_time=m.get("close_time"),
        game_date=_parse_game_date(event_ticker),
        expected_expiration_time=m.get("expected_expiration_time"),
        yes_team=yes_team,
        no_team=no_team,
    )


def get_available_game_dates(sample: int = 300) -> list[str]:
    """Return sorted unique game dates from a broad sample of open sports markets.

    Used to provide date hints when --date returns no results.
    Returns ISO date strings like ["2026-02-22", "2026-02-24"].
    """
    markets = _fetch_via_sports_series(target=sample)
    dates: set[str] = set()
    for m in markets:
        if m.game_date:
            dates.add(m.game_date.isoformat())
    return sorted(dates)


def _apply_filters(
    markets: list[MarketData],
    min_volume: int,
    min_open_interest: int,
) -> list[MarketData]:
    """Filter markets by minimum volume and open_interest (both in contracts)."""
    return [
        m for m in markets
        if m.volume >= min_volume and m.open_interest >= min_open_interest
    ]
