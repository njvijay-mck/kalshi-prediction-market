# Kalshi Prediction Market API Demos

A collection of 32 self-contained Python scripts demonstrating every major capability of the [Kalshi](https://kalshi.com) prediction market trading API. Targets the **demo environment** by default — safe to run without risking real money.

## Purpose

A hands-on learning resource covering:
- Public market data (exchange status, market discovery, orderbooks, candlesticks)
- Authenticated portfolio management (balance, positions, fills, settlements)
- Full order lifecycle (create, amend, decrease, cancel)
- Batch operations and order groups
- Historical data
- Real-time WebSocket streaming

---

## Prerequisites

- Python 3.9+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A Kalshi demo account at [demo.kalshi.co](https://demo.kalshi.co)
- An RSA key pair for API authentication

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

Edit `.env` and fill in your credentials:

```bash
KALSHI_API_KEY_ID=your-api-key-id-here
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem
KALSHI_ENV=demo
```

### 3. Get Kalshi demo API credentials

1. Sign up at [demo.kalshi.co](https://demo.kalshi.co)
2. Go to **Settings → API** in the demo dashboard
3. Generate a new API key and download your private key PEM file
4. Copy the Key ID into `KALSHI_API_KEY_ID` and the PEM path into `KALSHI_PRIVATE_KEY_PATH`

---

## Running Scripts

```bash
uv run python 01_exchange_info/01_exchange_status.py
```

All scripts are self-contained and print human-readable output. WebSocket scripts (folder `10_websocket/`) run until you press **Ctrl+C**.

---

## Directory Map

### `01_exchange_info/` — Public exchange metadata (no auth needed)
| Script | Description |
|--------|-------------|
| `01_exchange_status.py` | Health check — is trading active? |
| `02_exchange_schedule.py` | Trading hours and holiday calendar |
| `03_exchange_announcements.py` | Announcements with cursor pagination demo |

### `02_market_discovery/` — Browse markets (no auth needed)
| Script | Description |
|--------|-------------|
| `01_list_series.py` | Top-level market hierarchy (series) |
| `02_get_series.py` | Single series detail |
| `03_list_events.py` | Event listing with pagination |
| `04_get_event.py` | Event + embedded markets in one call |
| `05_list_markets.py` | Market filtering, `_fp`/`_dollars` fields |
| `06_get_market.py` | Full market schema, yes+no=100 relationship |

### `03_market_data/` — Price and trade data (no auth needed)
| Script | Description |
|--------|-------------|
| `01_get_orderbook.py` | L2 order book, depth, implied no asks |
| `02_get_candlesticks.py` | OHLCV candlestick data |
| `03_batch_candlesticks.py` | Multi-market candle fetch |
| `04_get_public_trades.py` | Public trade tape, taker_side |

### `04_portfolio/` — Account data (auth required, read-only)
| Script | Description |
|--------|-------------|
| `01_get_balance.py` | Account balance in dollars |
| `02_get_positions.py` | Open positions, cost basis |
| `03_get_fills.py` | Fill history with fees |
| `04_get_settlements.py` | Settled payouts |

### `05_orders/` — Order lifecycle (auth required, writes state)
| Script | Description |
|--------|-------------|
| `01_create_order.py` | Limit buy at 1¢, UUID idempotency |
| `02_get_order.py` | Order lookup, all status fields |
| `03_list_orders.py` | Filter by status, pagination |
| `04_amend_order.py` | Atomic cancel+rebook at new price |
| `05_decrease_order.py` | Partial size decrease |
| `06_cancel_order.py` | Cancel with error handling |
| `07_order_queue_position.py` | Queue position for resting orders |

### `06_batch_operations/` — Bulk order ops (auth required, writes state)
| Script | Description |
|--------|-------------|
| `01_batch_create_orders.py` | Submit multiple orders atomically |
| `02_batch_cancel_orders.py` | Cancel multiple orders (0.2 write units each) |

### `07_order_groups/` — Risk-contained order groups (auth required, writes state)
| Script | Description |
|--------|-------------|
| `01_create_order_group.py` | Group creation with contracts limit |
| `02_list_order_groups.py` | List all groups, per-group detail |
| `03_order_with_group.py` | Create order assigned to a group |
| `04_manage_order_group.py` | Trigger → reset → update → delete lifecycle |

### `08_historical/` — Historical market data (auth required, read-only)
| Script | Description |
|--------|-------------|
| `01_historical_cutoff.py` | Live/historical boundary timestamp |
| `02_historical_markets.py` | Browse settled markets |
| `03_historical_candlesticks.py` | Long-range daily candles for settled markets |
| `04_historical_fills.py` | Pre-cutoff fill history |

### `09_account_management/` — API key and rate limit info (auth required, read-only)
| Script | Description |
|--------|-------------|
| `01_get_api_keys.py` | API key list, metadata, expiration |
| `02_account_limits.py` | Rate limits, API tier, max connections |

### `10_websocket/` — Real-time streaming (async, Ctrl+C to stop)
| Script | Channel | Description |
|--------|---------|-------------|
| `01_ws_ticker.py` | `ticker` | L1 bid/ask for 3 markets |
| `02_ws_orderbook.py` | `orderbook_delta` | Live L2 order book with local state |
| `03_ws_public_trades.py` | `trade` | Real-time public trade tape |
| `04_ws_user_orders.py` | `user_orders` | Private order lifecycle events |
| `05_ws_user_fills.py` | `fill` | Private fill notifications |
| `06_ws_market_lifecycle.py` | `market_lifecycle_v2` | Market state changes and settlements |

---

## Recommended Running Order

| Wave | What to run | Requires |
|------|-------------|----------|
| 1 | `01_exchange_info/01_exchange_status.py` | Nothing — just verifies setup works |
| 2 | All of `02_market_discovery/` and `03_market_data/` | Nothing — public endpoints |
| 3 | All of `04_portfolio/`, `08_historical/`, `09_account_management/` | API credentials |
| 4 | All of `05_orders/`, `06_batch_operations/`, `07_order_groups/` | Credentials + demo env |
| 5 | All of `10_websocket/` | Credentials + demo env |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KALSHI_API_KEY_ID` | Yes (auth scripts) | Your API key ID from Kalshi dashboard |
| `KALSHI_PRIVATE_KEY_PATH` | Yes (auth scripts) | Absolute path to your RSA private key PEM |
| `KALSHI_ENV` | No | `demo` (default) or `prod` |
| `KALSHI_EXAMPLE_TICKER` | No | Pre-set a market ticker for examples |

---

## Key Concepts

- **Binary markets**: Every market has yes and no contracts. `yes_price + no_price = 100¢`.
- **`_fp` fields**: "fractional pennies" — raw integer cents. `_dollars` fields are the human-readable float.
- **Limit orders only**: Kalshi has no market order type; all orders are limit orders.
- **Demo env**: All scripts default to `demo-api.kalshi.co` — safe to experiment freely.
- **WebSocket auth**: Manually signed with RSA-PSS (the SDK doesn't expose a WS client). `build_ws_headers()` in `auth/client.py` handles this.
