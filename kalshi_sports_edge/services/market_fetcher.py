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
    SPORT_CATEGORIES,
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
    sports: list[str] | None = None,
) -> list[MarketData]:
    """Search open sports game markets whose title or ticker contains query.

    Fetches ALL markets from selected sports, sorts by volume descending,
    then applies filters and limit.
    
    Args:
        query: Search query string
        limit: Maximum number of markets to return
        min_volume: Minimum volume filter
        min_open_interest: Minimum open interest filter
        sports: Optional list of sports to filter by (e.g., ['soccer', 'tennis'])
    """
    # Fetch ALL markets from selected sports
    markets = _fetch_all_sports_markets(sports=sports)
    query_lower = query.lower()
    matched = [
        m for m in markets
        if query_lower in m.title.lower()
        or query_lower in m.ticker.lower()
        or query_lower in m.event_ticker.lower()
    ]
    # Sort by volume descending, then apply filters and limit
    sorted_markets = sorted(matched, key=lambda m: m.volume, reverse=True)
    return _apply_filters(sorted_markets, min_volume, min_open_interest)[:limit]


def fetch_by_date(
    game_date: datetime.date,
    limit: int = 50,
    min_volume: int = 0,
    min_open_interest: int = 0,
    sports: list[str] | None = None,
) -> list[MarketData]:
    """Fetch open sports markets whose game date matches game_date.

    Fetches ALL markets from selected sports, filters by game date,
    sorts by volume descending, then applies filters and limit.
    
    Args:
        game_date: Date to filter markets by
        limit: Maximum number of markets to return
        min_volume: Minimum volume filter
        min_open_interest: Minimum open interest filter
        sports: Optional list of sports to filter by (e.g., ['soccer', 'tennis'])
    """
    # Fetch ALL markets from selected sports
    markets = _fetch_all_sports_markets(sports=sports)
    on_date = [m for m in markets if m.game_date == game_date]
    # Sort by volume descending, then apply filters and limit
    sorted_markets = sorted(on_date, key=lambda m: m.volume, reverse=True)
    return _apply_filters(sorted_markets, min_volume, min_open_interest)[:limit]


def fetch_top_n(
    n: int,
    min_volume: int = 0,
    min_open_interest: int = 0,
    sports: list[str] | None = None,
) -> list[MarketData]:
    """Fetch top N open sports markets sorted by volume descending.
    
    Fetches ALL markets from selected sports, sorts by volume descending,
    then applies filters and returns top N.
    
    Args:
        n: Number of markets to return
        min_volume: Minimum volume filter
        min_open_interest: Minimum open interest filter
        sports: Optional list of sports to filter by (e.g., ['soccer', 'tennis'])
    """
    # Fetch ALL markets from selected sports
    markets = _fetch_all_sports_markets(sports=sports)
    # Sort by volume descending, then apply filters and limit
    sorted_markets = sorted(markets, key=lambda m: m.volume, reverse=True)
    filtered = _apply_filters(sorted_markets, min_volume, min_open_interest)
    return filtered[:n]


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


def _fetch_all_sports_markets(
    sports: list[str] | None = None,
) -> list[MarketData]:
    """Fetch ALL individual game markets from selected sports.

    For each series in US_SPORTS_GAME_SERIES (or filtered by sports):
      GET /events?series_ticker=<series>&status=open&with_nested_markets=true
    Markets embedded in each event are extracted and deduplicated by ticker.

    Fetches ALL markets from all selected series (no early stopping).
    
    Args:
        sports: Optional list of sports to filter by (e.g., ['soccer', 'tennis'])
    
    Returns:
        List of all MarketData objects from selected sports
    """
    seen: set[str] = set()
    results: list[MarketData] = []
    
    # Determine which series to fetch based on sports filter
    if sports:
        series_to_fetch: list[str] = []
        for sport in sports:
            sport_lower = sport.lower()
            if sport_lower in SPORT_CATEGORIES:
                series_to_fetch.extend(SPORT_CATEGORIES[sport_lower])
    else:
        series_to_fetch = US_SPORTS_GAME_SERIES

    for series_ticker in series_to_fetch:
        cursor: str | None = None
        while True:
            params: dict[str, object] = {
                "status": "open",
                "series_ticker": series_ticker,
                "limit": 50,
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


def _fetch_via_sports_series(
    target: int,
    sports: list[str] | None = None,
) -> list[MarketData]:
    """Fetch individual game markets by iterating known sports event series.

    DEPRECATED: Use _fetch_all_sports_markets() instead for full market fetching.
    This function is kept for backward compatibility with get_available_game_dates.
    
    For each series in US_SPORTS_GAME_SERIES (or filtered by sports):
      GET /events?series_ticker=<series>&status=open&with_nested_markets=true
    Markets embedded in each event are extracted and deduplicated by ticker.

    Stops when target market count is reached or all series are exhausted.
    
    Args:
        target: Target number of markets to fetch
        sports: Optional list of sports to filter by (e.g., ['soccer', 'tennis'])
    """
    seen: set[str] = set()
    results: list[MarketData] = []
    
    # Determine which series to fetch based on sports filter
    if sports:
        series_to_fetch: list[str] = []
        for sport in sports:
            sport_lower = sport.lower()
            if sport_lower in SPORT_CATEGORIES:
                series_to_fetch.extend(SPORT_CATEGORIES[sport_lower])
    else:
        series_to_fetch = US_SPORTS_GAME_SERIES

    for series_ticker in series_to_fetch:
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

# Kalshi markets expire roughly 3 hours after game tip-off.
# Subtracting this offset from expected_expiration_time gives the estimated
# game start time, whose LOCAL (ET) date is the true game date.
_GAME_START_OFFSET = datetime.timedelta(hours=3)
_ET = datetime.timezone(datetime.timedelta(hours=-5))


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

    Kalshi encodes YYMONDD in the second dash-separated segment.
    NOTE: this encodes the market *expiration* date (game end), not the game
    start date. Use _game_date_from_expiration() when expiration time is available.
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


def _game_date_from_expiration(iso_str: str | None) -> datetime.date | None:
    """Derive the game START date from expected_expiration_time.

    Kalshi markets expire ~3 h after tip-off. Subtracting _GAME_START_OFFSET
    and converting to ET gives the local date on which the game actually starts.

    Example: 10 PM ET Feb 28 tip-off → expiration ~1 AM ET Mar 1
             → 1 AM Mar 1 − 3 h = 10 PM Feb 28 ET → game_date = Feb 28 ✓
    Returns None if iso_str is absent or unparseable.
    """
    if not iso_str:
        return None
    try:
        dt_utc = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        start_et = (dt_utc - _GAME_START_OFFSET).astimezone(_ET)
        return start_et.date()
    except Exception:
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
    expected_expiration_time = m.get("expected_expiration_time")
    yes_team = m.get("yes_sub_title") or None
    no_team = _derive_opponent(event_title, yes_team) if yes_team and event_title else None
    # Prefer expiration-derived date (accurate game start date in ET) over
    # ticker-encoded date (which reflects market expiration, not game start).
    game_date = (
        _game_date_from_expiration(expected_expiration_time)
        or _parse_game_date(event_ticker)
    )
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
        game_date=game_date,
        expected_expiration_time=expected_expiration_time,
        yes_team=yes_team,
        no_team=no_team,
    )


def get_available_game_dates(
    sample: int = 300,
    sports: list[str] | None = None,
) -> list[str]:
    """Return sorted unique game dates from a broad sample of open sports markets.

    Used to provide date hints when --date returns no results.
    Returns ISO date strings like ["2026-02-22", "2026-02-24"].
    
    Args:
        sample: Number of markets to sample
        sports: Optional list of sports to filter by
    """
    markets = _fetch_via_sports_series(target=sample, sports=sports)
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
