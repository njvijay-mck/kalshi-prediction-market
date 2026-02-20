# Kalshi API Reference (Local Cache)

Quick reference for Kalshi prediction market API — REST and WebSocket.

---

## Authentication

### RSA-PSS Signing Formula

```
signature_input = timestamp_ms_string + HTTP_METHOD + path
```

Example for GET /trade-api/v2/exchange/status:
```
input = "1700000000000" + "GET" + "/trade-api/v2/exchange/status"
```

Sign with RSA-PSS, SHA-256, DIGEST_LENGTH salt.

### Required Headers (REST)

| Header | Value |
|--------|-------|
| `KALSHI-ACCESS-KEY` | Your API key ID |
| `KALSHI-ACCESS-TIMESTAMP` | Current Unix timestamp in milliseconds (string) |
| `KALSHI-ACCESS-SIGNATURE` | Base64-encoded RSA-PSS signature |

### WebSocket Auth

Sign `GET /trade-api/ws/v2` (same formula, no request body). Pass the three headers during the WebSocket handshake upgrade.

**Important:** Re-sign on every reconnect — stale timestamps are rejected.

---

## Base URLs

| Environment | REST | WebSocket |
|------------|------|-----------|
| Demo | `https://demo-api.kalshi.co/trade-api/v2` | `wss://demo-api.kalshi.co/trade-api/ws/v2` |
| Production | `https://api.elections.kalshi.com/trade-api/v2` | `wss://api.elections.kalshi.com/trade-api/ws/v2` |

---

## REST Endpoints Quick Reference

### Exchange (public)

| Method | Path | Auth | SDK Method |
|--------|------|------|------------|
| GET | `/exchange/status` | No | `client.get_exchange_status()` |
| GET | `/exchange/schedule` | No | `client.get_exchange_schedule()` |
| GET | `/exchange/announcements` | No | `client.get_exchange_announcements()` |

### Markets (public)

| Method | Path | Auth | SDK Method |
|--------|------|------|------------|
| GET | `/series` | No | `client.get_series()` |
| GET | `/series/{series_ticker}` | No | `client.get_series(series_ticker=...)` |
| GET | `/events` | No | `client.get_events()` |
| GET | `/events/{event_ticker}` | No | `client.get_event(event_ticker=...)` |
| GET | `/markets` | No | `client.get_markets()` |
| GET | `/markets/{ticker}` | No | `client.get_market(ticker=...)` |
| GET | `/markets/{ticker}/orderbook` | No | `client.get_market_orderbook(ticker=...)` |
| GET | `/markets/{ticker}/candlesticks` | No | `client.get_market_candlesticks(ticker=...)` |
| GET | `/trades` | No | `client.get_trades()` |

### Portfolio (auth required)

| Method | Path | Auth | SDK Method |
|--------|------|------|------------|
| GET | `/portfolio/balance` | Yes | `client.get_balance()` |
| GET | `/portfolio/positions` | Yes | `client.get_positions()` |
| GET | `/portfolio/fills` | Yes | `client.get_fills()` |
| GET | `/portfolio/settlements` | Yes | `client.get_settlements()` |

### Orders (auth required)

| Method | Path | Auth | SDK Method |
|--------|------|------|------------|
| POST | `/portfolio/orders` | Yes | `client.create_order(...)` |
| GET | `/portfolio/orders/{order_id}` | Yes | `client.get_order(order_id=...)` |
| GET | `/portfolio/orders` | Yes | `client.get_orders()` |
| POST | `/portfolio/orders/{order_id}/amend` | Yes | `client.amend_order(order_id=..., ...)` |
| POST | `/portfolio/orders/{order_id}/decrease` | Yes | `client.decrease_order(order_id=..., ...)` |
| DELETE | `/portfolio/orders/{order_id}` | Yes | `client.cancel_order(order_id=...)` |
| GET | `/portfolio/orders/{order_id}/queue_position` | Yes | `client.get_order_queue_position(order_id=...)` |

### Batch Operations (auth required)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/portfolio/orders/batched` | Yes | Multi-order submit |
| DELETE | `/portfolio/orders/batched` | Yes | Bulk cancel (0.2 write units each) |

### Order Groups (auth required)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/portfolio/order_groups` | Yes | Create group with limit |
| GET | `/portfolio/order_groups` | Yes | List all groups |
| GET | `/portfolio/order_groups/{group_id}` | Yes | Single group detail |
| PUT | `/portfolio/order_groups/{group_id}` | Yes | Update group limit |
| DELETE | `/portfolio/order_groups/{group_id}` | Yes | Delete group |
| POST | `/portfolio/order_groups/{group_id}/actions/trigger` | Yes | Trigger group |
| POST | `/portfolio/order_groups/{group_id}/actions/reset` | Yes | Reset triggered group |

### Historical (auth required)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/historical/cutoff` | Yes | Live/historical boundary |
| GET | `/historical/markets` | Yes | Settled markets |
| GET | `/historical/markets/{ticker}/candlesticks` | Yes | Historical candles |
| GET | `/historical/fills` | Yes | Pre-cutoff fill history |

### Account (auth required)

| Method | Path | Auth | SDK Method |
|--------|------|------|------------|
| GET | `/account/api_keys` | Yes | `client.get_api_keys()` |
| GET | `/account/limits` | Yes | direct HTTP or `client.get_account_limits()` |

---

## Market Structure

### Hierarchy
```
Series (e.g., "INXD" — S&P 500 Daily)
  └── Event (e.g., "INXD-25JAN24" — Jan 24 2025)
        └── Market (e.g., "INXD-25JAN24-T4800" — S&P above 4800)
```

### Binary Markets
- Every market has **yes** and **no** contracts
- `yes_price + no_price = 100` (always, in cents)
- Prices in cents: 1¢ = near impossible, 99¢ = near certain
- Only **limit orders** — no market order type

### Field Naming
- `_fp` suffix: raw integer cents (fractional pennies), e.g., `yes_price_fp = 45` means 45¢
- `_dollars` suffix: float dollars, e.g., `count_fp = 500` → 5 contracts (500 ÷ 100)
- Prefer `_dollars` and `_fp` fields over bare field names (deprecated)

### Orderbook Structure
- **Only yes-side bids** are stored in the book
- No asks on yes side = equivalent to yes bids on no side
- `depth` parameter: number of price levels to return

---

## WebSocket Channels

### Subscribe Command Format
```json
{
  "id": 1,
  "cmd": "subscribe",
  "params": {
    "channels": ["ticker"],
    "market_tickers": ["INXD-25JAN24-T4800", "KXBTCD-25JAN24"]
  }
}
```

Note: `market_lifecycle_v2` and `order_group_updates` channels do NOT use `market_tickers`.

### Channel Reference

| Channel | Auth | Key Fields | Notes |
|---------|------|-----------|-------|
| `ticker` | No | `yes_bid`, `yes_ask`, `last_price`, `volume` | L1 per-market updates |
| `orderbook_delta` | No | `market_ticker`, `side`, `price`, `delta_fp` | Snapshot + incremental L2 |
| `trade` | No | `yes_price`, `count_fp`, `taker_side` | Public trade tape |
| `user_orders` | Yes | `order_id`, `status`, `remaining_count_fp` | Private order events |
| `fill` | Yes | `order_id`, `count_fp`, `fee_cost` | Private fill notifications |
| `market_lifecycle_v2` | No | `status`, `settlement_value` | Market state changes |
| `user_balance` | Yes | `balance` | Balance change events |
| `order_group_updates` | Yes | `group_id`, `status` | Group state changes |
| `user_positions` | Yes | `position_fp` | Position change events |

### Orderbook Snapshot + Delta Protocol
1. First message type `orderbook_snapshot`: replace local state entirely
2. Subsequent `orderbook_delta` messages: apply `delta_fp` to existing qty at price level
3. Delete level if resulting qty ≤ 0
4. Re-render after each update

### WebSocket Behavior
- Kalshi sends pings every ~10s
- `websockets` library auto-responds with pong — set `ping_interval=None` in `connect()`
- Reconnect with exponential backoff (1s → 2s → 4s → ... → 60s cap)

---

## Order Reference

### Order Fields
```python
{
    "ticker": "INXD-25JAN24-T4800",
    "side": "yes",          # "yes" or "no"
    "action": "buy",        # "buy" or "sell"
    "type": "limit",        # always "limit"
    "count_fp": 100,        # contracts × 100 (1 contract = 100 fp)
    "yes_price_dollars": 0.01,     # 1¢ — safe test price
    "client_order_id": "uuid-here" # for idempotency
}
```

### Order Status Values
- `resting` — in the order book, not yet filled
- `filled` — fully executed
- `partially_filled` — partially executed, still resting
- `canceled` — canceled (manually or on expiry)
- `pending` — submitted but not yet accepted

### Rate Limits by API Tier

| Tier | Read / 10s | Write / 10s |
|------|-----------|-------------|
| Basic | 20 | 10 |
| Advanced | 30 | 30 |
| Premier | 100 | 100 |
| Prime | 400 | 400 |

- Batch cancel: each individual cancel = 0.2 write units (vs 1.0 for single cancel)
- Batch create: 1 write unit per batch call regardless of order count

---

## Pagination

All list endpoints use cursor-based pagination.

### Pattern
```python
cursor = None
while True:
    resp = client.get_markets(limit=200, cursor=cursor)
    items.extend(resp.markets)
    if not resp.cursor:
        break
    cursor = resp.cursor
```

- Pass `cursor=None` (or omit) for the first page
- Each response has a `.cursor` attribute — `None` or empty string means last page
- `limit` defaults vary by endpoint; max is usually 200 or 1000

---

## SDK Usage Pattern

```python
from kalshi_python_sync import Configuration, KalshiClient

config = Configuration(host="https://demo-api.kalshi.co/trade-api/v2")
config.api_key_id = "your-key-id"
config.private_key_pem = open("/path/to/key.pem").read()

client = KalshiClient(config)

# All methods are flat on the client object:
status = client.get_exchange_status()
markets = client.get_markets(status="open", limit=10)
balance = client.get_balance()
order = client.create_order(ticker="...", side="yes", action="buy",
                            type="limit", count_fp=100, yes_price_dollars=0.01)
```

The SDK handles RSA-PSS signing automatically for REST calls.
For WebSocket, use `build_ws_headers()` from `auth/client.py` to sign manually.
