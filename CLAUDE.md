# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

32 self-contained Python demo scripts covering the full Kalshi prediction market REST and WebSocket API. Each script is standalone and prints human-readable output.

**Plus:** `kalshi_sports_edge/` — A comprehensive sports prediction market analysis tool with LLM-powered deep research, multi-source web search, and professional reporting.

## Toolchain

- **Package manager:** `uv` — run `uv sync` to install, `uv run python <script>` to execute
- **Linter/formatter:** `ruff`
- **Type checker:** `mypy`

## Common Commands

```bash
uv sync                                               # Install/update dependencies
uv run python 01_exchange_info/01_exchange_status.py  # Run any script
uv run python -m kalshi_sports_edge --help           # Sports edge CLI help
uv run ruff check .                                   # Lint
uv run ruff format .                                  # Format
uv run mypy .                                         # Type check
```

---

# Kalshi Sports Edge Module

## Overview

`kalshi_sports_edge/` is a professional-grade sports prediction market analysis system that:
- Fetches live sports markets from Kalshi API
- Performs multi-source web research (Reddit, Yahoo, ESPN, X)
- Uses LLM to estimate true probabilities
- Calculates Edge, EV, and ROI
- Generates consolidated reports (terminal + PDF)

## Architecture

```
kalshi_sports_edge/
├── cli.py              # CLI argument parsing (--sports, --deep-research, etc.)
├── config.py           # Sports categories, series tickers, API settings
├── models.py           # Dataclasses: MarketData, OddsTable, MarketAnalysis, etc.
├── orchestrator.py     # Main coordinator, routes CLI args to pipelines
├── output/
│   ├── terminal.py     # Rich terminal output (8-section reports)
│   └── pdf_report.py   # PDF generation with professional styling
└── services/
    ├── deep_research.py    # 5-stage pipeline with web search
    ├── llm_pipeline.py     # Single-pass LLM analysis
    ├── market_fetcher.py   # Kalshi API market fetching
    ├── market_utils.py     # Market grouping utilities
    ├── odds_engine.py      # Odds calculations
    └── web_search.py       # Multi-source Brave search
```

## Sports Categories

Supported sports with series tickers:

| Sport | Series Count | Examples |
|-------|--------------|----------|
| **Basketball** | 19 | NBA, WNBA, NCAA, Euroleague, VTB, ACB |
| **Football** | 3 | NFL, NCAAF, D3 |
| **Baseball** | 2 | MLB, NCAA |
| **Soccer** | 39 | MLS, EPL, La Liga, Bundesliga, Champions League |
| **Tennis** | 38 | ATP, WTA, Grand Slams, Challengers |
| **Hockey** | 5 | NHL, NCAA, KHL, IIHF, AHL |

## CLI Usage

```bash
# Basic usage
uv run python -m kalshi_sports_edge --pick 10 --summary

# Filter by sport
uv run python -m kalshi_sports_edge --pick 10 --sports soccer
uv run python -m kalshi_sports_edge --pick 20 --sports basketball soccer tennis

# Deep research with web search
uv run python -m kalshi_sports_edge --pick 10 --deep-research --web-search

# Specific date with sport filter
uv run python -m kalshi_sports_edge --date 2026-03-01 --sports basketball --deep-research

# Output formats
uv run python -m kalshi_sports_edge --pick 5 --deep-research --pdf        # PDF report
uv run python -m kalshi_sports_edge --pick 5 --deep-research --verbose    # Show web context
```

## Deep Research Pipeline (5 Stages)

1. **Multi-Source Web Research** — Parallel searches across:
   - Reddit (r/nba, r/sportsbook, etc.)
   - Yahoo Sports
   - ESPN
   - X/Twitter
   - General web

2. **Probability Estimation** — LLM estimates true probabilities using web context

3. **Metrics Calculation**:
   - `Edge = LLM% - Market%`
   - `EV/c = Edge` (when positive)
   - `ROI = EV / MarketPrice × 100`

4. **Classification**:
   - Sentiment: Bullish / Neutral / Bearish
   - Confidence: High / Medium / Low
   - Reason: stats, injury, form, news, data, record, consensus, volume, schedule, weather, momentum, unclear

5. **Consolidation** — Generate rankings and recommendations

## Report Sections (8 Sections)

1. **Header** — Timestamp, market count, model info
2. **Summary Table** — All markets with Edge, EV, Sentiment, ROI, Rec, Conf, Why
3. **Top Picks by Edge** — |Edge| ≥ 5%, ranked by magnitude
4. **Top Picks by EV** — Positive EV only, ranked
5. **Markets to Avoid** — No edge or negative EV
6. **Mini Odds Overview** — Per-market detailed breakdown
7. **Why Column Legend** — Explanation of reason tags
8. **Footer** — Disclaimer

## Key Data Models

### MarketData
- `ticker`, `title`, `event_ticker`, `category`
- `yes_bid`, `yes_ask`, `last_price`, `volume`, `open_interest`
- `game_date`, `yes_team`, `no_team`
- `mid_price`, `spread_cents`

### OddsTable
- `yes_row`, `no_row` (OddsRow with price, implied_prob, decimal_odds, american_odds)
- `overround`, `price_source`, `wide_spread`

### MarketAnalysis (Deep Research)
- `market`, `odds_table`
- `llm_yes_prob`, `llm_no_prob`
- `yes_edge`, `no_edge`, `yes_ev`, `no_ev`, `yes_roi`, `no_roi`
- `best_edge`, `best_ev`, `best_side`, `best_roi`
- `sentiment`, `confidence`, `reason`
- `web_context`, `llm_analysis`

## Environment Variables

```bash
# Required for authenticated endpoints
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=kalshi.pem
KALSHI_ENV=demo  # or "prod"

# Required for web search
BRAVE_SEARCH_API_KEY=your-brave-key

# Required for LLM analysis
ANTHROPIC_API_KEY=your-claude-key    # for --provider claude
KIMI_API_KEY=your-kimi-key           # for --provider kimi
MOONSHOT_API_KEY=your-moonshot-key   # for --provider moonshot
```

---

# API Demo Scripts

## Auth Module (`auth/client.py`)

Every script imports from here. Key exports:

```python
from auth.client import get_client       # KalshiClient (sync REST, kalshi_python_sync)
from auth.client import raw_get          # Authenticated GET → dict (bypasses SDK pydantic)
from auth.client import raw_post         # Authenticated POST → dict
from auth.client import raw_delete       # Authenticated DELETE → dict
from auth.client import get_ws_url       # WebSocket base URL
from auth.client import build_ws_headers # RSA-PSS signed headers for WS handshake
```

`get_client()` and `raw_get()` both work **without credentials** for public endpoints (they skip auth headers when env vars are absent).

## Environment

`.env` file (copy from `.env.example`):

```bash
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=kalshi.pem   # relative or absolute path to PEM file
# "demo" or "prod"
KALSHI_ENV=demo
# optional ticker override
KALSHI_EXAMPLE_TICKER=
```

> **Critical:** Never put inline comments after `=` values — python-dotenv includes them in the value. Put comments on separate lines.

`KALSHI_ENV=demo` → `demo-api.kalshi.co`
`KALSHI_ENV=prod` → `api.elections.kalshi.com`
API keys are environment-specific — a prod key returns `NOT_FOUND` (401) on demo and vice versa.

## SDK Quirks (kalshi_python_sync v3.2.0)

### SDK client pattern

`KalshiClient` uses `__getattr__` to delegate flat method calls to internal sub-APIs:

```python
client = get_client()
client.get_balance()        # → PortfolioApi.get_balance()
client.create_order(...)    # → OrdersApi.create_order(...)
```

### When to use `raw_get()` vs SDK

Many endpoints fail with `pydantic.ValidationError` because the API returns `null` for fields the SDK models require. Use `raw_get()` for these:

| Endpoint category | Use `raw_get`? | Reason |
|------------------|----------------|--------|
| `GET /series`, `/events`, `/markets` | **Yes** | Null `category`, `tags`, `risk_limit_cents` |
| `GET /markets/{ticker}/orderbook` | **Yes** | SDK model field issues |
| `GET /portfolio/orders/queue_positions` | **Yes** | Returns null list |
| `GET /portfolio/orders/{id}/queue_position` | **Yes** | SDK pydantic failure |
| `GET /historical/*` | **Yes** | SDK methods don't exist yet |
| `GET /account/limits` | **Yes** | SDK method not available |
| `get_balance()`, `get_positions()`, `get_fills()`, `get_settlements()` | **No** | SDK works |
| `create_order()`, `cancel_order()`, `amend_order()`, etc. | **No** | SDK works |
| `batch_create_orders()`, `batch_cancel_orders()` | **No** | SDK works |
| `create_order_group()`, `get_order_groups()`, etc. | **No** | SDK works |
| `get_market_candlesticks()` | **No** | SDK works |
| `get_trades()` | **No** | SDK works |

### Correct SDK method and field names

```python
# Orders — use int, not fp variants
client.create_order(
    ticker=ticker, side="yes", action="buy", type="limit",
    count=1,          # int contracts (NOT count_fp)
    yes_price=1,      # int cents 1-99 (NOT yes_price_dollars=0.01)
    client_order_id=str(uuid.uuid4()),
)

# Amend — BOTH client_order_id (original) AND updated_client_order_id (new) are required
client.amend_order(
    order_id=oid, ticker=ticker, side="yes", action="buy", count=1, yes_price=2,
    client_order_id=original_uuid,           # required
    updated_client_order_id=new_uuid,        # required
)

# Decrease
client.decrease_order(order_id=oid, reduce_by=3)   # int (NOT reduce_by_fp)

# Batch cancel
client.batch_cancel_orders(ids=[oid1, oid2])       # field is 'ids' (NOT order_ids)

# Order groups — kwarg is order_group_id= (NOT group_id=)
client.get_order_group(order_group_id=gid)
client.reset_order_group(order_group_id=gid)
client.delete_order_group(order_group_id=gid)

# Candlesticks — BOTH series_ticker AND ticker required
series_ticker = event_ticker.rsplit("-", 2)[0]
client.get_market_candlesticks(
    series_ticker=series_ticker, ticker=ticker,
    start_ts=start_ts, end_ts=end_ts, period_interval=60,
)
```

### SDK response field types (confirmed on prod)

- `Order.status` → `OrderStatus` enum (e.g. `OrderStatus.RESTING`), not a plain string
- `MarketPosition.market_exposure_dollars` → `str` like `'9.2300'` — use `float()` before formatting
- `Fill.created_time` → `datetime.datetime` object (not string or int)
- `Settlement.settled_time` → `datetime.datetime` object
- `MarketCandlestick.price` → `PriceDistribution` with `.open`, `.high`, `.low`, `.close`, `.mean` (int cents) and `.*_dollars` (str)

## Historical API Field Names

The historical endpoints use different field names than the portfolio endpoints:

| Data | Field name |
|------|-----------|
| Cutoff timestamp | `market_settled_ts` (ISO string), also `orders_updated_ts`, `trades_created_ts` |
| Market settle date | `settlement_ts` (ISO string) — NOT `settled_time` |
| Market outcome | `result` (`"yes"` or `"no"`) — NOT `market_result` |
| Candle prices | Dollar strings (e.g. `"0.5500"` = 55¢) when non-null; `null` for zero-volume |

## WebSocket Architecture (`10_websocket/`)

All 6 scripts share the same skeleton:
- Connect with `build_ws_headers()` — **re-sign on every reconnect** (stale timestamps rejected by server)
- `ping_interval=None` — Kalshi sends pings every ~10s, `websockets` auto-pongs
- Exponential backoff reconnect: 1→2→4→…→60s cap
- Clean Ctrl+C via `asyncio.Event` + `loop.add_signal_handler` (Linux/WSL2)

Channels that do **not** take `market_tickers` in the subscribe params:
- `user_orders`, `fill`, `market_lifecycle_v2`

Channels that **do** take `market_tickers`:
- `ticker`, `orderbook_delta`, `trade`

Use `raw_get("/markets", status="open", limit=N)` to get tickers — never `client.get_markets()` (pydantic fails).

## Folder/Script Map

```
auth/client.py              # shared auth — every script imports this
docs/kalshi_api_reference.md # local API reference

01_exchange_info/           # SDK works for all 3 (public)
02_market_discovery/        # all use raw_get (pydantic fails on demo/prod null fields)
03_market_data/             # raw_get for market lookup; SDK for candlesticks/trades
04_portfolio/               # SDK works (read-only, auth)
05_orders/                  # SDK works; queue_position uses raw_get
06_batch_operations/        # SDK works
07_order_groups/            # SDK works; param is order_group_id= not group_id=
08_historical/              # all use raw_get (SDK methods don't exist)
09_account_management/      # get_api_keys: SDK; account_limits: raw_get
10_websocket/               # raw websockets lib + build_ws_headers(); raw_get for tickers

kalshi_sports_edge/         # Sports prediction market analysis tool
```

## API Reference

`docs/kalshi_api_reference.md` — local copy covering auth, endpoints, market structure, WebSocket channels, order fields, pagination, and rate limits.
