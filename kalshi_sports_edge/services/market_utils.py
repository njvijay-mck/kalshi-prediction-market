"""Utility functions for market grouping and deduplication."""

from __future__ import annotations

from kalshi_sports_edge.models import GameGroup, MarketData


def group_markets_by_game(markets: list[MarketData]) -> list[GameGroup]:
    """Group markets by event_ticker to combine both sides of binary markets.

    For each game (e.g., Spurs vs Pistons), this creates a GameGroup containing
    both YES markets (Spurs YES and Pistons YES).

    Returns list of GameGroups sorted by combined volume descending.
    """
    # Group by event_ticker
    by_event: dict[str, list[MarketData]] = {}
    for m in markets:
        key = m.event_ticker
        if key not in by_event:
            by_event[key] = []
        by_event[key].append(m)

    game_groups: list[GameGroup] = []

    for event_ticker, event_markets in by_event.items():
        if len(event_markets) < 2:
            # Single-sided market, skip or handle as incomplete
            continue

        # Sort by ticker to get consistent ordering
        event_markets = sorted(event_markets, key=lambda m: m.ticker)

        # Get team info - use yes_team from each market
        team_a = event_markets[0]
        team_b = event_markets[1]

        # Extract abbreviations from ticker suffix
        team_a_abbrev = _extract_team_abbrev(team_a.ticker)
        team_b_abbrev = _extract_team_abbrev(team_b.ticker)

        # Use yes_team if available, otherwise use abbrev
        team_a_name = team_a.yes_team or team_a_abbrev or "Team A"
        team_b_name = team_b.yes_team or team_b_abbrev or "Team B"

        game_groups.append(
            GameGroup(
                event_ticker=event_ticker,
                game_date=team_a.game_date,
                expected_expiration_time=team_a.expected_expiration_time,
                team_a_name=team_a_name,
                team_a_abbrev=team_a_abbrev or "A",
                team_a_market=team_a,
                team_b_name=team_b_name,
                team_b_abbrev=team_b_abbrev or "B",
                team_b_market=team_b,
            )
        )

    # Sort by combined volume descending
    game_groups.sort(key=lambda g: g.combined_volume, reverse=True)
    return game_groups


def _extract_team_abbrev(ticker: str) -> str | None:
    """Extract team abbreviation from market ticker.

    Example: KXNBAGAME-26FEB23SASDET-SAS -> SAS
             KXNBAGAME-26FEB23SASDET-DET -> DET
    """
    parts = ticker.split("-")
    if len(parts) >= 3:
        return parts[-1]  # Last part is the team abbrev
    return None
