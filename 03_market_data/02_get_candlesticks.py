"""03_market_data/02_get_candlesticks.py

Demonstrates: GET /series/{series_ticker}/markets/{ticker}/candlesticks
- OHLCV candlestick data for a single market.
- period_interval: minutes per candle (1, 5, 15, 60, 240, 1440).
- Public endpoint: no credentials needed.

SDK method: get_market_candlesticks(series_ticker, ticker, start_ts, end_ts, period_interval)
Note: Requires BOTH series_ticker AND ticker.
MarketCandlestick fields: end_period_ts, yes_bid, yes_ask, price, volume, open_interest

Run:
    uv run python 03_market_data/02_get_candlesticks.py
"""

import datetime
import os

from auth.client import get_client, raw_get

PERIOD_INTERVAL = 60  # 1-hour candles
MAX_CANDLES = 10

client = get_client()

ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
series_ticker = ""
if not ticker:
    data = raw_get("/markets", status="open", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets found — cannot continue.")
        raise SystemExit(1)
    m = markets[0]
    ticker = m["ticker"]
    event_ticker = m.get("event_ticker", "")
    print(f"(Using market: {ticker}, event: {event_ticker})\n")
    series_ticker = event_ticker.rsplit("-", 2)[0] if event_ticker else ticker.rsplit("-", 2)[0]
else:
    series_ticker = ticker.rsplit("-", 2)[0]

now = datetime.datetime.now(datetime.timezone.utc)
start_ts = int((now - datetime.timedelta(days=1)).timestamp())
end_ts = int(now.timestamp())

print(f"=== Candlesticks: {ticker} ({PERIOD_INTERVAL}m candles, last 24h) ===")
print(f"  series_ticker: {series_ticker}\n")
print(f"{'Time (UTC)':^22}  {'Price':>6}  {'Volume':>10}  {'Open Interest':>14}")
print("-" * 58)

# Use SDK method — it takes series_ticker + ticker
try:
    resp = client.get_market_candlesticks(
        series_ticker=series_ticker,
        ticker=ticker,
        period_interval=PERIOD_INTERVAL,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    candles = resp.candlesticks or []
    source = "SDK"
except Exception as exc:
    # Fall back to raw HTTP
    print(f"  (SDK failed: {exc} — using raw HTTP)\n")
    data = raw_get(
        f"/series/{series_ticker}/markets/{ticker}/candlesticks",
        period_interval=PERIOD_INTERVAL,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    candles = data.get("candlesticks", [])
    source = "raw HTTP"

for candle in (candles[-MAX_CANDLES:] if hasattr(candles, '__len__') else candles):
    if hasattr(candle, 'end_period_ts'):
        # SDK object
        ts_raw = candle.end_period_ts
        price = candle.price
        volume = candle.volume
        open_interest = candle.open_interest
    else:
        # dict from raw HTTP
        ts_raw = candle.get("end_period_ts")
        price = candle.get("price")
        volume = candle.get("volume")
        open_interest = candle.get("open_interest")

    ts_str = ""
    if ts_raw:
        dt = datetime.datetime.fromtimestamp(ts_raw, tz=datetime.timezone.utc)
        ts_str = dt.strftime("%Y-%m-%d %H:%M")

    print(f"{ts_str:^22}  {str(price):>5}¢  {str(volume):>10}  {str(open_interest):>14}")

if not candles:
    print("No candlestick data returned for this period.")

candle_list = list(candles) if not isinstance(candles, list) else candles
print(f"\nTotal candles: {len(candle_list)} (source: {source})")
print("MarketCandlestick fields: end_period_ts, yes_bid, yes_ask, price, volume, open_interest")
print("Note: Kalshi candlesticks are point-in-time snapshots, not OHLCV bars")
