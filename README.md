# Kalshi Prediction Market API Demos

A collection of 32 self-contained Python scripts demonstrating every major capability of the [Kalshi](https://kalshi.com) prediction market trading API — public market data, authenticated portfolio management, full order lifecycle, batch operations, order groups, historical data, and real-time WebSocket streaming.

---

## Prerequisites

- Python 3.9+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A Kalshi account ([demo.kalshi.co](https://demo.kalshi.co) or [kalshi.com](https://kalshi.com))
- An RSA private key for API authentication

---

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` — put comments on **separate lines** (inline comments after `=` are parsed as part of the value by python-dotenv):

```bash
# "demo" or "prod"
KALSHI_ENV=demo
KALSHI_API_KEY_ID=your-api-key-id-here
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem
# optional: pre-set a market ticker
KALSHI_EXAMPLE_TICKER=
```

> **Important:** `KALSHI_PRIVATE_KEY_PATH` can be a relative path (e.g. `kalshi.pem` if the file is in the project root) or an absolute path.

### 3. Get API credentials

**Demo account:**
1. Sign up at [demo.kalshi.co](https://demo.kalshi.co)
2. Go to **Settings → API** → generate a key pair
3. Set `KALSHI_ENV=demo`

**Production account:**
1. Sign up at [kalshi.com](https://kalshi.com)
2. Go to **Settings → API** → generate a key pair
3. Set `KALSHI_ENV=prod`

> Credentials are environment-specific — a prod key will return `NOT_FOUND` on the demo endpoint, and vice versa.

---

## Running Scripts

```bash
uv run python 01_exchange_info/01_exchange_status.py
```

All scripts are self-contained and print human-readable output. WebSocket scripts (`10_websocket/`) run until you press **Ctrl+C**.

---

## Directory Map

### `01_exchange_info/` — Public exchange metadata (no auth)
| Script | SDK Method | Description |
|--------|-----------|-------------|
| `01_exchange_status.py` | `client.get_exchange_status()` | Health check — is trading active? |
| `02_exchange_schedule.py` | `client.get_exchange_schedule()` | Trading hours, per-day windows |
| `03_exchange_announcements.py` | `client.get_exchange_announcements()` | Announcements, cursor pagination |

### `02_market_discovery/` — Browse markets (no auth, uses `raw_get`)
| Script | Endpoint | Description |
|--------|---------|-------------|
| `01_list_series.py` | `GET /series` | Top-level market hierarchy |
| `02_get_series.py` | `GET /series/{ticker}` | Single series detail |
| `03_list_events.py` | `GET /events` | Events with cursor pagination |
| `04_get_event.py` | `GET /events/{ticker}` | Event + nested markets in one call |
| `05_list_markets.py` | `GET /markets` | Market filtering, `_dollars` fields |
| `06_get_market.py` | `GET /markets/{ticker}` | Full market schema, yes+no=100 |

> These use `raw_get()` instead of the SDK because the SDK's pydantic models reject null fields returned by the API for some market attributes (`category`, `tags`, `risk_limit_cents`).

### `03_market_data/` — Price and trade data (no auth)
| Script | Description |
|--------|-------------|
| `01_get_orderbook.py` | L2 order book, yes bids only, implied no asks |
| `02_get_candlesticks.py` | OHLCV candles — `price.open/high/low/close` in cents |
| `03_batch_candlesticks.py` | Multi-market candle fetch loop |
| `04_get_public_trades.py` | Public trade tape, taker_side |

### `04_portfolio/` — Account data (auth required, read-only)
| Script | SDK Method | Description |
|--------|-----------|-------------|
| `01_get_balance.py` | `client.get_balance()` | Balance in cents → divide by 100 for dollars |
| `02_get_positions.py` | `client.get_positions()` | Open positions, `_dollars` fields are strings |
| `03_get_fills.py` | `client.get_fills()` | Fill history, `created_time` is a datetime object |
| `04_get_settlements.py` | `client.get_settlements()` | Settled payouts, revenue in cents |

### `05_orders/` — Order lifecycle (auth required, writes state)
| Script | Description |
|--------|-------------|
| `01_create_order.py` | Limit buy at 1¢ — `count=1` (int contracts), `yes_price=1` (int cents) |
| `02_get_order.py` | Order lookup, all status fields |
| `03_list_orders.py` | Filter by status (resting/filled/canceled), pagination |
| `04_amend_order.py` | Atomic cancel+rebook — requires both `client_order_id` and `updated_client_order_id` |
| `05_decrease_order.py` | Partial size reduction — keeps queue position |
| `06_cancel_order.py` | Cancel with error handling |
| `07_order_queue_position.py` | Queue position — uses `raw_get` (SDK pydantic fails on null result) |

### `06_batch_operations/` — Bulk order ops (auth required, writes state)
| Script | Description |
|--------|-------------|
| `01_batch_create_orders.py` | Submit multiple orders in one API call (1 write unit total) |
| `02_batch_cancel_orders.py` | Cancel multiple orders (0.2 write units each) |

### `07_order_groups/` — Risk-contained order groups (auth required, writes state)
| Script | Description |
|--------|-------------|
| `01_create_order_group.py` | Create group with `contracts_limit` |
| `02_list_order_groups.py` | List groups, fetch per-group detail |
| `03_order_with_group.py` | Create order assigned to a group via `order_group_id=` |
| `04_manage_order_group.py` | Full lifecycle: create → get → reset → delete |

> SDK uses `order_group_id=` (not `group_id=`) for `get_order_group`, `reset_order_group`, `delete_order_group`.

### `08_historical/` — Historical market data (auth required, read-only)
| Script | Description |
|--------|-------------|
| `01_historical_cutoff.py` | Cutoff boundary — returns `market_settled_ts`, `orders_updated_ts`, `trades_created_ts` |
| `02_historical_markets.py` | Settled markets — uses `settlement_ts` and `result` fields |
| `03_historical_candlesticks.py` | Daily candles for settled markets (last 730 days) |
| `04_historical_fills.py` | Pre-cutoff fill history |

### `09_account_management/` — API key and rate limit info (auth required, read-only)
| Script | Description |
|--------|-------------|
| `01_get_api_keys.py` | API key list, name, scopes |
| `02_account_limits.py` | Rate limits (`read_limit`, `write_limit`, `usage_tier`) |

### `10_websocket/` — Real-time streaming (async, Ctrl+C to stop)
| Script | Channel | Auth | Description |
|--------|---------|------|-------------|
| `01_ws_ticker.py` | `ticker` | Yes | L1 bid/ask stream for 3 markets |
| `02_ws_orderbook.py` | `orderbook_delta` | Yes | Live L2 book — snapshot + delta → local state |
| `03_ws_public_trades.py` | `trade` | Yes | Real-time public trade tape |
| `04_ws_user_orders.py` | `user_orders` | Yes | Private order lifecycle events (no market_tickers) |
| `05_ws_user_fills.py` | `fill` | Yes | Private fill notifications (no market_tickers) |
| `06_ws_market_lifecycle.py` | `market_lifecycle_v2` | Yes | Market state changes, settlement events (no market_tickers) |

---

## Recommended Running Order

| Wave | Scripts | Requires |
|------|---------|----------|
| 1 | `01_exchange_info/01_exchange_status.py` | Nothing — verifies connectivity |
| 2 | All of `02_market_discovery/` and `03_market_data/` | Nothing — public endpoints |
| 3 | All of `04_portfolio/`, `08_historical/`, `09_account_management/` | API credentials (read-only) |
| 4 | All of `05_orders/`, `06_batch_operations/`, `07_order_groups/` | Credentials + (use demo for safety) |
| 5 | All of `10_websocket/` | Credentials — streams until Ctrl+C |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KALSHI_API_KEY_ID` | For auth scripts | Key ID from Kalshi dashboard |
| `KALSHI_PRIVATE_KEY_PATH` | For auth scripts | Path to RSA private key PEM (relative or absolute) |
| `KALSHI_ENV` | No | `demo` (default) or `prod` |
| `KALSHI_EXAMPLE_TICKER` | No | Pre-set a market ticker to skip auto-selection |

---

## Key Concepts

### Market structure
- **Series → Events → Markets** hierarchy
- Binary markets: `yes_price + no_price = 100¢` always
- Prices are integers in cents (1–99); `_dollars` fields are string representations like `"0.5500"`

### Orders
- **Limit orders only** — no market order type
- `count=1` means 1 contract (integer, not fractional)
- `yes_price=1` means 1¢ (integer 1–99)
- `client_order_id` (UUID) enables idempotent submission

### Candlesticks
- `MarketCandlestick.price` is a `PriceDistribution` object with `open`, `high`, `low`, `close`, `mean` (cents) and `*_dollars` string fields
- `get_market_candlesticks()` requires **both** `series_ticker` and `ticker`

### `raw_get()` pattern
Many SDK calls fail with `pydantic.ValidationError` on demo/prod because the API returns `null` for fields the models require. `raw_get()` in `auth/client.py` bypasses the SDK and returns a plain dict:

```python
from auth.client import raw_get
data = raw_get("/markets", status="open", limit=10)
markets = data.get("markets", [])
```

### WebSocket
- Auth headers are manually RSA-PSS signed — **re-sign on every reconnect** (stale timestamps rejected)
- `ping_interval=None` — Kalshi sends pings every ~10s; the `websockets` library auto-responds
- All 6 scripts include exponential-backoff reconnect (1→2→4→…→60s) and clean Ctrl+C shutdown

### Rate limits (Basic tier defaults)
| Operation | Cost |
|-----------|------|
| Single read | 1 read unit |
| Single write (order create/cancel/amend) | 1 write unit |
| Batch cancel per order | 0.2 write units |
| Batch create (entire call) | 1 write unit |

---

## Project Structure

```
kalshi-prediction-market/
├── pyproject.toml          # uv/hatch project config
├── .env.example            # credential template
├── auth/
│   ├── __init__.py
│   └── client.py           # shared auth: get_client, raw_get, build_ws_headers
├── docs/
│   └── kalshi_api_reference.md   # local API reference
├── 01_exchange_info/       # 3 scripts — public
├── 02_market_discovery/    # 6 scripts — public
├── 03_market_data/         # 4 scripts — public
├── 04_portfolio/           # 4 scripts — auth, read-only
├── 05_orders/              # 7 scripts — auth, writes
├── 06_batch_operations/    # 2 scripts — auth, writes
├── 07_order_groups/        # 4 scripts — auth, writes
├── 08_historical/          # 4 scripts — auth, read-only
├── 09_account_management/  # 2 scripts — auth, read-only
└── 10_websocket/           # 6 scripts — auth, async streaming
```
