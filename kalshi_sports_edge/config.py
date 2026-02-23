"""Application-level constants and configuration for kalshi_sports_edge."""

from __future__ import annotations

import os
from dataclasses import dataclass

# --- Sports filtering ---
SPORTS_CATEGORY = "Sports"

# Known Kalshi series tickers for individual US sports game markets.
# These are fetched via /events?series_ticker=X rather than the flat /markets
# endpoint (which returns KXMVESPORTSMULTIGAMEEXTENDED parlay markets first).

# --- BASKETBALL ---
BASKETBALL_SERIES: list[str] = [
    "KXNBAGAME",     # NBA  — Professional Basketball Game
    "KXNCAAMBGAME",  # NCAAB — Men's College Basketball Game
    "KXNCAAWBGAME",  # NCAAW — Women's College Basketball Game
    "KXWNBAGAME",    # WNBA  — Professional Women's Basketball Game
    "KXNBAGAMES",    # NBA games (alt series)
    "KXUNRIVALEDGAME",  # Unrivaled Basketball Game
    "KXVTBGAME",     # VTB United League Game
    "KXELHGAME",     # ELH (Czech) Game
    "KXGBLGAME",     # GBL (Greek) Game
    "KXACBGAME",     # Liga ACB (Spain) Game
    "KXEUROLEAGUEGAME",  # Euroleague Game
    "KXLNBELITEGAME",    # LNB Elite (France) Game
    "KXBSLGAME",     # Turkey BSL Game
    "KXJBLEAGUEGAME",    # Japan B League Game
    "KXKBLGAME",     # Korea KBL Game
    "KXCBAGAME",     # Chinese Basketball Association Game
    "KXNBLGAME",     # NBL (Australia) Game
    "KXABAGAME",     # ABA League Game
    "KXBBSERIEAGAME",    # Italy Serie A Basketball Game
]

# --- FOOTBALL ---
FOOTBALL_SERIES: list[str] = [
    "KXNFLGAME",     # NFL  — Professional Football Game
    "KXNCAAFGAME",   # NCAAF — College Football Game
    "KXNCAAFD3GAME", # D3 College Football Game
]

# --- BASEBALL ---
BASEBALL_SERIES: list[str] = [
    "KXMLBGAME",     # MLB  — Professional Baseball Game
    "KXNCAAMBBGAME", # College Baseball Game
]

# --- SOCCER / FOOTBALL ---
SOCCER_SERIES: list[str] = [
    "KXMLSGAME",         # Major League Soccer Game
    "KXLALIGAGAME",      # La Liga Game (Spain)
    "KXEPLGAME",         # English Premier League Game
    "KXBUNDESLIGAGAME",  # Bundesliga Game (Germany)
    "KXUCLGAME",         # UEFA Champions League Game
    "KXUELGAME",         # UEFA Europa League Game
    "KXUECLGAME",        # UEFA Conference League Game
    "KXJLEAGUEGAME",     # Japan J League Game
    "KXALEAGUEGAME",     # Australian A League Game
    "KXLIGAMXGAME",      # Liga MX Game (Mexico)
    "KXLIGUE1GAME",      # Ligue 1 Game (France)
    "KXARGPREMDIVGAME",  # Argentina Primera Division Game
    "KXBRASILEIROGAME",  # Brasileiro Serie A Game (Brazil)
    "KXSCOTTISHPREMGAME",# Scottish Premiership Game
    "KXEREDIVISIEGAME",  # Eredivisie Game (Netherlands)
    "KXBELGIANPLGAME",   # Belgian Pro League Game
    "KXSWISSLEAGUEGAME", # Swiss Super League Game
    "KXEKSTRAKLASAGAME", # Polish Ekstraklasa Game
    "KXHNLGAME",         # Croatia HNL Game
    "KXLIIGAGAME",       # Liiga Game (Finland)
    "KXSHLGAME",         # SHL Game (Sweden)
    "KXDANISHSUPERLIGAGAME", # Danish Superliga Game
    "KXSAUDIPLSPREAD",   # Saudi Pro League Game
    "KXKNVBCUPGAME",     # KNVB Cup Game (Netherlands)
    "KXDFBPOKALGAME",    # DFB Pokal Game (Germany)
    "KXTACAPORTGAME",    # Taca de Portugal Game
    "KXFACUPGAME",       # FA Cup Game (England)
    "KXCOPADELREYGAME",  # Copa Del Rey Game (Spain)
    "KXCOPPAITALIAGAME", # Coppa Italia Game
    "KXITASUPERCUPGAME", # Italy Super Cup Game
    "KXEFLCHAMPIONSHIPGAME", # EFL Championship Game
    "KXLALIGA2GAME",     # LaLiga 2 Game
    "KXBUNDESLIGA2GAME", # Bundesliga 2 Game
    "KXINTLFRIENDLYGAME",# International Friendly Game
    "KXWCGAME",          # World Cup Game
    "KXAFCONGAME",       # AFCON Game
    "KXASIACUPGAME",     # Asia Cup Game
    "KXCONCACAFGAME",    # CONCACAF Game
    "KXCOPAAMERICAGAME", # Copa America Game
]

# --- TENNIS ---
TENNIS_SERIES: list[str] = [
    "KXATPMATCH",         # ATP Tennis Match
    "KXWTAMATCH",         # WTA Tennis Match
    "KXATPCHALLENGERMATCH", # Challenger ATP
    "KXWTACHALLENGERMATCH", # Challenger WTA
    "KXATPDOUBLES",       # ATP Doubles Tennis Match
    "KXWTADOUBLES",       # WTA Doubles Tennis Match
    "KXFOMENSINGLES",     # French Open men's singles
    "KXFOWOMENSINGLES",   # French Open women's singles
    "KXUSOMENSINGLES",    # US Open men's singles
    "KXUSOWOMENSINGLES",  # US Open women's singles
    "KXAOMENSINGLES",     # Australian Open men's singles
    "KXWOWOMENSINGLES",   # Wimbledon women's singles
    "KXDDFMENSINGLES",    # Dubai Duty Free Men's Singles
    "KXWTASERENA",        # Serena Williams WTA
    "KXWTAIWO",           # Indian Wells Open (WTA)
    "KXATPIWO",           # Indian Wells Open (ATP)
    "KXATPMIA",           # ATP Miami
    "KXWTAMIA",           # WTA Miami
    "KXATPMAD",           # ATP Madrid
    "KXWTAMAD",           # WTA Madrid
    "KXATPIT",            # ATP Italian Open
    "KXWTAIT",            # WTA Italian Open
    "KXATPMC",            # ATP Monte Carlo
    "KXATPMCO",           # Movistar Chile Open
    "KXATPWDDF",          # ATP Dubai Duty Free
    "KXWTADDF",           # WTA Dubai Duty Free
    "KXWTAATX",           # WTA Tour ATX Open
    "KXWTAMOA",           # WTA Tour Merida Open Akron
    "KXATPAMT",           # ATP Tour Abierto Mexican
    "KXATPGRANDSLAM",     # ATP Grand Slam
    "KXWTAGRANDSLAM",     # WTA Grand Slam
    "KXTENNISGRANDSLAM",  # Tennis Grand Slam
    "KXUSOPEN",           # US Open (generic)
    "KXATPFINALS",        # ATP Finals Winner
    "KXWTAFINALS",        # WTA Finals Champion
    "KXATPANYSET",        # ATP Any Set Winner
    "KXATPTOTALSETS",     # ATP Total Sets
    "KXTABLETENNIS",      # Table Tennis Match
]

# --- HOCKEY ---
HOCKEY_SERIES: list[str] = [
    "KXNHLGAME",      # NHL Game
    "KXNCAAHOCKEYGAME", # College Hockey Game
    "KXIIHFGAME",     # IIHF Game
    "KXKHLGAME",      # KHL Game
    "KXAH LGAME",     # AHL Game
]

# Combined list for backward compatibility
US_SPORTS_GAME_SERIES: list[str] = (
    BASKETBALL_SERIES
    + FOOTBALL_SERIES
    + BASEBALL_SERIES
    + SOCCER_SERIES
    + TENNIS_SERIES
    + HOCKEY_SERIES
)

# Ticker prefixes that identify individual sports game markets
# (used in is_sports_market() as a fast prefix check on event_ticker)
SPORTS_TICKER_PREFIXES: tuple[str, ...] = tuple(
    BASKETBALL_SERIES
    + FOOTBALL_SERIES
    + BASEBALL_SERIES
    + SOCCER_SERIES
    + TENNIS_SERIES
    + HOCKEY_SERIES
)

# Sport category mapping for filtering
SPORT_CATEGORIES: dict[str, list[str]] = {
    "basketball": BASKETBALL_SERIES,
    "football": FOOTBALL_SERIES,
    "baseball": BASEBALL_SERIES,
    "soccer": SOCCER_SERIES,
    "tennis": TENNIS_SERIES,
    "hockey": HOCKEY_SERIES,
}

# All supported sports (for CLI help text)
SUPPORTED_SPORTS: list[str] = list(SPORT_CATEGORIES.keys())

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
