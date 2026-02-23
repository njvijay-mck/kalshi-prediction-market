"""Application-level constants and configuration for kalshi_sports_edge."""

from __future__ import annotations

import os
from dataclasses import dataclass

# --- Sports filtering ---
SPORTS_CATEGORY = "Sports"

# Known Kalshi series tickers for individual US sports game markets.
# These are fetched via /events?series_ticker=X rather than the flat /markets
# endpoint (which returns KXMVESPORTSMULTIGAMEEXTENDED parlay markets first).
US_SPORTS_GAME_SERIES: list[str] = [
    "KXNBAGAME",     # NBA  — Professional Basketball Game
    "KXNFLGAME",     # NFL  — Professional Football Game
    "KXMLBGAME",     # MLB  — Professional Baseball Game
    "KXNHLGAME",     # NHL  — NHL Game
    "KXNCAAFGAME",   # NCAAF — College Football Game
    "KXNCAAMBGAME",  # NCAAB — Men's College Basketball Game
    "KXNCAAWBGAME",  # NCAAW — Women's College Basketball Game
    "KXWNBAGAME",    # WNBA  — Professional Women's Basketball Game
    "KXNBAGAMES",    # NBA games (alt series)
]

# Ticker prefixes that identify individual sports game markets
# (used in is_sports_market() as a fast prefix check on event_ticker)
SPORTS_TICKER_PREFIXES: tuple[str, ...] = (
    "KXNBAGAME", "KXNFLGAME", "KXMLBGAME", "KXNHLGAME",
    "KXNCAAFGAME", "KXNCAAMBGAME", "KXNCAAWBGAME", "KXWNBAGAME",
)

# --- Odds engine ---
WIDE_SPREAD_THRESHOLD = 10  # cents; spreads above this trigger a terminal warning

# --- API pacing ---
RATE_LIMIT_SLEEP_S = 0.1   # sleep between paginated Kalshi requests (20 reads/10s limit)
MAX_PAGE_SIZE = 200         # maximum limit param per /markets page

# --- Defaults ---
EDGE_THRESHOLD_DEFAULT = 0.05
DEFAULT_LIMIT = 10
DEFAULT_MIN_VOLUME = 0
DEFAULT_MIN_OI = 0

# --- LLM providers ---
# - claude: Anthropic Claude API (Anthropic SDK)
# - kimi: Kimi Code API (Anthropic SDK with custom base URL)
# - moonshot: Standard Moonshot AI API (OpenAI-compatible SDK)
PROVIDER_BASE_URLS: dict[str, str] = {
    "claude": "https://api.anthropic.com",  # Anthropic SDK adds /v1
    "kimi": "https://api.kimi.com/coding",  # Anthropic SDK adds /v1, Kimi uses Anthropic format
    "moonshot": "https://api.moonshot.cn/v1",  # OpenAI-compatible
}

PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "claude": "claude-opus-4-6",
    "kimi": "kimi-for-coding",
    "moonshot": "kimi-k2-5",
}

PROVIDER_ENV_KEYS: dict[str, str] = {
    "claude": "ANTHROPIC_API_KEY",
    "kimi": "KIMI_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
}


@dataclass
class AppConfig:
    llm_provider: str = "claude"
    llm_model: str = "claude-opus-4-6"
    edge_threshold: float = EDGE_THRESHOLD_DEFAULT
    min_volume: int = DEFAULT_MIN_VOLUME
    min_open_interest: int = DEFAULT_MIN_OI
    limit: int = DEFAULT_LIMIT
    pdf_output_dir: str = "reports"
    verbose: bool = False
    brave_api_key: str | None = None


def load_config() -> AppConfig:
    """Build AppConfig from environment variables and defaults."""
    return AppConfig(
        brave_api_key=os.getenv("BRAVE_SEARCH_API_KEY"),
    )
