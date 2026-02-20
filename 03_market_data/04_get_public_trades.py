"""03_market_data/04_get_public_trades.py

Demonstrates: client.get_trades(ticker=..., limit=20)
- Public trade tape — every executed trade.
- Shows taker_side (the aggressing side of the trade).
- Public endpoint: no credentials needed.

SDK method: get_trades(ticker, limit, cursor, min_ts, max_ts)
SDK response type: GetTradesResponse
  .trades -> list[Trade]
  .cursor -> str | None
    Trade fields: trade_id, ticker, price, count, yes_price, no_price,
                  yes_price_dollars, no_price_dollars, taker_side, created_time

Run:
    uv run python 03_market_data/04_get_public_trades.py
"""

import datetime
import os

from auth.client import get_client, raw_get

LIMIT = 20

client = get_client()

ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not ticker:
    # Use most-active market
    data = raw_get("/markets", status="open", limit=20)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets — cannot continue.")
        raise SystemExit(1)
    markets_sorted = sorted(markets, key=lambda m: m.get("volume") or 0, reverse=True)
    ticker = markets_sorted[0]["ticker"]
    print(f"(Using most active market: {ticker})\n")

print(f"=== Public Trades: {ticker} (last {LIMIT}) ===\n")
print(f"{'Time (UTC)':^22}  {'Yes Price':>10}  {'Count':>8}  {'Taker':>8}")
print("-" * 55)

resp = client.get_trades(ticker=ticker, limit=LIMIT)
trades = resp.trades or []

for trade in trades:
    ts_str = ""
    if trade.created_time:
        if isinstance(trade.created_time, str):
            dt = datetime.datetime.fromisoformat(trade.created_time.replace("Z", "+00:00"))
        elif isinstance(trade.created_time, (int, float)):
            dt = datetime.datetime.fromtimestamp(trade.created_time, tz=datetime.timezone.utc)
        else:
            dt = trade.created_time
        ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"{ts_str:^22}  {str(trade.yes_price):>9}¢  {str(trade.count):>8}  "
        f"{str(trade.taker_side):>8}  id:{str(trade.trade_id)[:10]}..."
    )

if not trades:
    print("No trades found for this market.")

print(f"\nTotal trades shown: {len(trades)}")
print("\nField notes:")
print("  yes_price  : execution price in cents (1-99)")
print("  count      : contracts traded (integer)")
print("  taker_side : 'yes' or 'no' — the aggressing side that crossed the spread")
print("  price      : generic price field (same as yes_price for yes-side taker)")
