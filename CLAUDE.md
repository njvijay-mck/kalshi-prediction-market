# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project

32 self-contained Python demo scripts covering the full Kalshi prediction market REST and WebSocket API, plus `kalshi_sports_edge/` — a sports prediction market analysis tool with LLM research and PDF reporting.

## Toolchain

- **Package manager:** `uv` (`uv sync` to install, `uv run python <script>` to execute)
- **Linter/formatter:** `ruff` | **Type checker:** `mypy`

```bash
uv sync
uv run python 01_exchange_info/01_exchange_status.py
uv run python -m kalshi_sports_edge --help
uv run ruff check . && uv run ruff format .
uv run mypy .
```

---

# API Demo Scripts (01–10)

## Auth Module (`auth/client.py`)

Every script imports from here:

```python
from auth.client import get_client       # KalshiClient (kalshi_python_sync v3.2.0)
from auth.client import raw_get          # GET → dict, bypasses pydantic
from auth.client import raw_post         # POST → dict
from auth.client import raw_delete       # DELETE → dict
from auth.client import get_ws_url       # WebSocket base URL
from auth.client import build_ws_headers # RSA-PSS signed WS headers
```

Works without credentials for public endpoints.

## Environment (`.env`)

```bash
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=kalshi.pem
KALSHI_ENV=demo                  # or "prod"
KALSHI_EXAMPLE_TICKER=           # optional
```

> **Critical:** No inline comments after `=` — python-dotenv includes them in the value.

`KALSHI_ENV=demo` → `demo-api.kalshi.co` | `KALSHI_ENV=prod` → `api.elections.kalshi.com`
API keys are environment-specific — cross-env use returns 401.

## SDK Quirks (kalshi_python_sync v3.2.0)

`KalshiClient` uses `__getattr__` delegation (flat method calls to internal sub-APIs).

### raw_get() vs SDK

| Endpoint | Use `raw_get`? | Why |
|----------|---------------|-----|
| `/series`, `/events`, `/markets` | **Yes** | Null `category`, `tags`, `risk_limit_cents` |
| `/markets/{ticker}/orderbook` | **Yes** | SDK model field issues |
| `/portfolio/orders/*/queue_position*` | **Yes** | SDK pydantic failure |
| `/historical/*` | **Yes** | SDK methods don't exist |
| `/account/limits` | **Yes** | SDK method missing |
| `get_balance/positions/fills/settlements/orders/order` | No | SDK works |
| `create/cancel/amend/decrease_order` | No | SDK works |
| `batch_create/cancel_orders` | No | SDK works |
| `create/get/reset/delete_order_group` | No | SDK works |
| `get_market_candlesticks`, `get_trades` | No | SDK works |

### SDK Method Gotchas

```python
# Orders: use int, not fp variants
client.create_order(ticker=t, side="yes", action="buy", type="limit",
    count=1, yes_price=1, client_order_id=str(uuid.uuid4()))

# Amend: BOTH client_order_id (original) AND updated_client_order_id (new) required
client.amend_order(order_id=oid, ...,
    client_order_id=orig_uuid, updated_client_order_id=new_uuid)

client.decrease_order(order_id=oid, reduce_by=3)          # int, NOT reduce_by_fp
client.batch_cancel_orders(ids=[oid1, oid2])              # 'ids', NOT 'order_ids'
client.get_order_group(order_group_id=gid)                # order_group_id=, NOT group_id=
client.reset_order_group(order_group_id=gid)
client.delete_order_group(order_group_id=gid)

# Candlesticks: BOTH series_ticker AND ticker required
series_ticker = event_ticker.rsplit("-", 2)[0]
client.get_market_candlesticks(series_ticker=series_ticker, ticker=ticker,
    start_ts=start_ts, end_ts=end_ts, period_interval=60)
```

### SDK Response Types

- `Order.status` → `OrderStatus` enum (not str)
- `MarketPosition.market_exposure_dollars` → `str` like `'9.2300'` — use `float()` before formatting
- `Fill.created_time`, `Settlement.settled_time` → `datetime.datetime`
- `MarketCandlestick.price` → `PriceDistribution` with `.open/.high/.low/.close/.mean` (int cents) and `.*_dollars` (str)

## Historical API Field Names

| Data | Field |
|------|-------|
| Cutoff timestamps | `market_settled_ts`, `orders_updated_ts`, `trades_created_ts` (ISO str) |
| Market settle date | `settlement_ts` — NOT `settled_time` |
| Market outcome | `result` ("yes"/"no") — NOT `market_result` |
| Candle prices | Dollar strings e.g. `"0.5500"` = 55¢; `null` for zero-volume |

## WebSocket Architecture (`10_websocket/`)

- Re-sign `build_ws_headers()` on every reconnect (stale timestamps rejected)
- `ping_interval=None` — server pings every ~10s, `websockets` auto-pongs
- Exponential backoff: 1→2→4→…→60s | Clean Ctrl+C via `asyncio.Event` + signal handler

Channels **without** `market_tickers`: `user_orders`, `fill`, `market_lifecycle_v2`
Channels **with** `market_tickers`: `ticker`, `orderbook_delta`, `trade`

Use `raw_get("/markets", status="open", limit=N)` for tickers — never `client.get_markets()`.

## Folder/Script Map

```
auth/client.py              # shared auth — every script imports this
docs/kalshi_api_reference.md # local API reference

01_exchange_info/   # 3 scripts: status, schedule, announcements (SDK, public)
02_market_discovery/# 6 scripts: series→events→markets (all raw_get, pydantic fails)
03_market_data/     # 4 scripts: orderbook (raw_get), candlesticks/trades (SDK)
04_portfolio/       # 4 scripts: balance, positions, fills, settlements (SDK, auth)
05_orders/          # 7 scripts: full lifecycle (SDK); queue_position uses raw_get
06_batch_operations/# 2 scripts: batch create/cancel (SDK)
07_order_groups/    # 4 scripts: create, list, order-with-group, manage (SDK)
08_historical/      # 4 scripts: cutoff, markets, candlesticks, fills (all raw_get)
09_account_management/ # 2 scripts: api_keys (SDK), account_limits (raw_get)
10_websocket/       # 6 scripts: ticker, orderbook, trades, user_orders, fills, lifecycle
```

---

# Kalshi Sports Edge Module

## Overview

`kalshi_sports_edge/` — CLI tool for sports prediction market analysis.

```bash
uv run python -m kalshi_sports_edge --pick 10 --summary
uv run python -m kalshi_sports_edge --pick 10 --sports soccer basketball
uv run python -m kalshi_sports_edge --pick 10 --deep-research --web-search
uv run python -m kalshi_sports_edge --date 2026-03-01 --sports basketball --deep-research
uv run python -m kalshi_sports_edge --pick 5 --deep-research --pdf --verbose
```

**CLI flags:** `--ticker`, `--search`, `--date`, `--pick N` (market source, mutually exclusive)
`--sports [basketball|football|baseball|soccer|tennis|hockey]`, `--limit N`, `--min-volume N`
`--exclude-started`, `--llm`, `--provider [claude|kimi|moonshot]`, `--model NAME`
`--deep-research`, `--web-search`, `--edge-threshold 0.05`, `--pdf`, `--verbose`, `--summary`

> **Critical:** Demo env has no real sports markets. Set `KALSHI_ENV=prod`.

## Architecture

```
kalshi_sports_edge/
├── __main__.py         # Entry point: load .env → parse args → run orchestrator
├── cli.py              # CLIArgs dataclass + parse_args()
├── config.py           # Sports series tickers, LLM providers, AppConfig
├── models.py           # MarketData, OddsRow, OddsTable, GameGroup, MarketAnalysis,
│                       # ReportData, ConsolidatedReport, RunMetrics
├── orchestrator.py     # run(CLIArgs) → routes to pipelines, outputs reports
├── services/
│   ├── market_fetcher.py   # fetch_by_ticker/keyword/date/top_n(); sports via events endpoint
│   ├── odds_engine.py      # calc_market_odds(), calc_edge(), calc_ev()
│   ├── web_search.py       # search_game_context() → MultiSourceContext (Reddit/Yahoo/ESPN/X)
│   ├── llm_pipeline.py     # get_llm_client(), run_single_pass()
│   ├── deep_research.py    # run_deep_research() → 5-stage pipeline → ConsolidatedReport
│   └── market_utils.py     # group_markets_by_game() → list[GameGroup]
└── output/
    ├── terminal.py     # print_enhanced_consolidated_report(), print_volume_summary(), etc.
    └── pdf_report.py   # write_enhanced_consolidated_report() → reports/YYYY-MM-DD/*.pdf
```

## Sports Series (config.py)

| Sport | Series |
|-------|--------|
| Basketball | 19 (NBA, WNBA, NCAA, Euroleague, VTB, ACB, …) |
| Football | 3 (NFL, NCAAF, D3) |
| Baseball | 2 (MLB, NCAA) |
| Soccer | 39 (MLS, EPL, La Liga, Bundesliga, Champions League, …) |
| Tennis | 38 (ATP, WTA, Grand Slams, Challengers, …) |
| Hockey | 5 (NHL, NCAA, KHL, IIHF, AHL) |

Total: 106 series in `US_SPORTS_GAME_SERIES`.

## LLM Providers

| Provider | Env Key | Default Model | SDK |
|----------|---------|---------------|-----|
| `claude` (default) | `ANTHROPIC_API_KEY` | `claude-opus-4-6` | `anthropic` |
| `kimi` | `KIMI_API_KEY` | `kimi-for-coding` | `anthropic` (different base_url) |
| `moonshot` | `MOONSHOT_API_KEY` | `kimi-k2-5` | `openai` |

Web search: `BRAVE_SEARCH_API_KEY`

## Market Fetching Strategy

Sports markets are fetched via events endpoint (NOT flat `/markets`):
```
/events?series_ticker=KXNBAGAME&status=open&with_nested_markets=true
```
Flat `/markets?status=open` returns parlay markets (`KXMVESPORTSMULTIGAMEEXTENDED`) first — individual game markets are buried thousands of pages deep.

Markets embedded in events have `status='active'` (not `'open'`).
Zero prices (`yes_bid=0`, `yes_ask=0`, `last_price=0`) treated as absent; valid range is 1–99 cents.

## Key Data Models

**MarketData:** `ticker, title, event_ticker, category, yes_bid, yes_ask, last_price, volume, open_interest, game_date, yes_team, no_team` | props: `mid_price, spread_cents, no_price`

**OddsTable:** `yes_row, no_row` (OddsRow: `price_cents, implied_prob, decimal_odds, american_odds, fractional_str, edge`) | `overround, price_source, wide_spread`

**MarketAnalysis:** `market, odds_table, llm_yes_prob, llm_no_prob, yes_edge, no_edge, yes_ev, no_ev, yes_roi, no_roi, best_edge, best_ev, best_side, best_roi, sentiment, confidence, reason, web_context, llm_analysis`

## Deep Research Pipeline (5 Stages)

1. **Web Research** — Parallel searches: Reddit, Yahoo Sports, ESPN, X, general web
2. **Probability Estimation** — LLM estimates true probabilities with web context
3. **Metrics** — `Edge = LLM% - Market%` | `EV = Edge / implied` | `ROI = EV / price × 100`
4. **Classification** — Sentiment: Bullish/Neutral/Bearish | Confidence: High/Medium/Low | Reason: stats/injury/form/news/data/record/consensus/volume/schedule/weather/momentum/unclear
5. **Consolidation** — Rankings and recommendations

## Report Output (8 Sections)

Header → Summary Table (Edge/EV/Sentiment/ROI/Rec/Conf/Why) → Top Picks by Edge (≥5%) → Top Picks by EV → Markets to Avoid → Mini Odds Overview → Why Legend → Footer/Disclaimer

PDF saved to `reports/YYYY-MM-DD/consolidated_{HHMMSS}.pdf`.

## API Reference

`docs/kalshi_api_reference.md` — auth, endpoints, market structure, WebSocket channels, orders, pagination, rate limits.
`docs/kalshi_sports_edge_spec.md` — comprehensive spec for the sports edge module.
