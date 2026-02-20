"""04_portfolio/03_get_fills.py

Demonstrates: client.get_fills(limit=20)
- Your personal fill history (private — only your trades).
- Requires credentials in .env

SDK method: get_fills(limit, cursor, ticker, min_ts, max_ts)
SDK response type: GetFillsResponse
  .fills -> list[Fill]
  .cursor -> str | None

Fill fields:
  fill_id, trade_id, order_id, client_order_id,
  ticker, market_ticker, side, action, count, price,
  yes_price, no_price, is_taker, created_time, ts

Run:
    uv run python 04_portfolio/03_get_fills.py
"""

import datetime

from auth.client import get_client

LIMIT = 20

client = get_client()

print("=== Fill History (your trades) ===\n")
resp = client.get_fills(limit=LIMIT)
fills = resp.fills or []

if not fills:
    print("No fills found.")
    print("Create and fill an order in 05_orders/ to see fills here.")
else:
    print(f"{'Time':^22}  {'Ticker':<28}  {'Side':>5}  {'Action':>6}  {'Price':>7}  {'Count':>6}  {'Taker':>6}")
    print("-" * 90)
    for fill in fills:
        ts_str = ""
        if fill.created_time:
            if isinstance(fill.created_time, str):
                dt = datetime.datetime.fromisoformat(fill.created_time.replace("Z", "+00:00"))
            elif isinstance(fill.created_time, (int, float)):
                dt = datetime.datetime.fromtimestamp(fill.created_time, tz=datetime.timezone.utc)
            else:
                dt = fill.created_time
            ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        print(
            f"{ts_str:^22}  {fill.ticker:<28}  {str(fill.side):>5}  "
            f"{str(fill.action):>6}  {str(fill.yes_price):>6}¢  {str(fill.count):>6}  "
            f"{'yes' if fill.is_taker else 'no':>6}"
        )

if resp.cursor:
    print(f"\nMore fills (cursor: {resp.cursor!r})")

print(f"\nTotal fills shown: {len(fills)}")
print("\nField notes:")
print("  side    : 'yes' or 'no' — which contract side you traded")
print("  action  : 'buy' or 'sell'")
print("  yes_price: execution price in cents")
print("  count   : contracts traded (integer, not fp)")
print("  is_taker: True if you were the aggressor crossing the spread")
