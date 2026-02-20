"""03_market_data/03_batch_candlesticks.py

Demonstrates: Multi-market candlestick fetch (loop over markets)
- Fetches 60-minute candles for the 3 most-active open markets.
- MarketCandlestick has price/yes_bid/yes_ask as PriceDistribution objects with
  open, high, low, close, mean fields — actual OHLCV is per-period!
- Public endpoint: no credentials needed.

SDK method: get_market_candlesticks(series_ticker, ticker, start_ts, end_ts, period_interval)
PriceDistribution fields: open, high, low, close, mean (all in cents)
                         + open_dollars, high_dollars, low_dollars, close_dollars

Run:
    uv run python 03_market_data/03_batch_candlesticks.py
"""

import datetime

from auth.client import get_client, raw_get

NUM_MARKETS = 3
PERIOD_INTERVAL = 60  # 1-hour candles
CANDLES_TO_SHOW = 3

client = get_client()

# Pick the most-active open markets
data = raw_get("/markets", status="open", limit=20)
markets = data.get("markets", [])
markets_sorted = sorted(markets, key=lambda m: m.get("volume") or 0, reverse=True)
selected = markets_sorted[:NUM_MARKETS]

now = datetime.datetime.now(datetime.timezone.utc)
start_ts = int((now - datetime.timedelta(days=1)).timestamp())
end_ts = int(now.timestamp())

print("=== Batch Candlestick Fetch ===\n")
print("MarketCandlestick price fields are PriceDistribution objects with open/high/low/close/mean.\n")

for m in selected:
    ticker = m["ticker"]
    event_ticker = m.get("event_ticker", "")
    series_ticker = event_ticker.rsplit("-", 2)[0] if event_ticker else ticker.rsplit("-", 2)[0]

    try:
        candle_resp = client.get_market_candlesticks(
            series_ticker=series_ticker,
            ticker=ticker,
            period_interval=PERIOD_INTERVAL,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        candles = candle_resp.candlesticks or []

        print(f"  {ticker} (series={series_ticker}): {len(candles)} candles")
        for candle in candles[-CANDLES_TO_SHOW:]:
            ts_str = ""
            if candle.end_period_ts:
                dt = datetime.datetime.fromtimestamp(candle.end_period_ts, tz=datetime.timezone.utc)
                ts_str = dt.strftime("%H:%M UTC")

            # Price is a PriceDistribution object with open/high/low/close/mean
            price = candle.price
            open_p = price.open if price else None
            high_p = price.high if price else None
            low_p = price.low if price else None
            close_p = price.close if price else None

            print(
                f"    {ts_str}  O={open_p}¢ H={high_p}¢ L={low_p}¢ C={close_p}¢  "
                f"vol={candle.volume}  oi={candle.open_interest}"
            )
        print()
    except Exception as exc:
        print(f"  {ticker}: error — {exc}\n")

print("Key insight: Kalshi candlesticks DO have OHLCV data via PriceDistribution.")
print("  candle.price.open, .high, .low, .close, .mean  (all in cents)")
print("  candle.price.open_dollars, .close_dollars, etc.  (float dollars)")
print("  Same structure for candle.yes_bid and candle.yes_ask")
