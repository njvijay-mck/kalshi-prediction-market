"""08_historical/03_historical_candlesticks.py

Demonstrates: GET /historical/markets/{ticker}/candlesticks
- Long-range daily (1440-minute) candles for a settled market.
- Historical markets are not available in the standard candlestick endpoint.
- Requires credentials in .env

Run:
    uv run python 08_historical/03_historical_candlesticks.py
"""

import datetime
import os

from auth.client import get_client, raw_get

PERIOD_INTERVAL = 1440  # daily candles
MAX_CANDLES = 30

client = get_client()

print("=== Historical Candlesticks (daily) ===\n")

# Find a settled historical market
ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not ticker:
    data = raw_get("/historical/markets", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No historical markets found. Run 08_historical/02_historical_markets.py first.")
        raise SystemExit(1)
    m = markets[0]
    ticker = m.get("ticker", "") if isinstance(m, dict) else getattr(m, "ticker", "")
    if not ticker:
        print("Could not determine ticker from historical markets.")
        raise SystemExit(1)
    print(f"(Using first historical market: {ticker})\n")

now = datetime.datetime.now(datetime.timezone.utc)
# Use wide range to cover historical markets (often 1-2 years old)
start_ts = int((now - datetime.timedelta(days=730)).timestamp())
end_ts = int(now.timestamp())

data = raw_get(
    f"/historical/markets/{ticker}/candlesticks",
    period_interval=PERIOD_INTERVAL,
    start_ts=start_ts,
    end_ts=end_ts,
)
candles = data.get("candlesticks", data.get("candles", []))

print(f"Ticker: {ticker}  |  period_interval={PERIOD_INTERVAL}m (daily)")
print(f"Date range: last 730 days\n")
print(f"{'Date (UTC)':^12}  {'Open':>6}  {'High':>6}  {'Low':>6}  {'Close':>6}  {'Volume':>10}")
print("-" * 55)

def _extract_price_cents(p: object) -> str:
    """Extract price value from various formats the API may return."""
    if p is None:
        return "?"
    if isinstance(p, dict):
        # Might be {"open": 55, "close": 60, ...} or {"yes_price": 55}
        val = p.get("close", p.get("yes_price", p.get("cents", "?")))
        return f"{val}¢"
    if isinstance(p, (int, float)):
        return f"{p}¢"
    # SDK PriceDistribution object
    val = getattr(p, "close", getattr(p, "yes_price", getattr(p, "cents", "?")))
    return f"{val}¢"

def _to_cents(val: object) -> str:
    """Convert a price value (cents int, dollar string, or None) to display string."""
    if val is None:
        return "?"
    if isinstance(val, (int, float)):
        return f"{val}¢"
    if isinstance(val, str):
        try:
            return f"{round(float(val) * 100)}¢"
        except ValueError:
            return val
    return "?"

for candle in candles[-MAX_CANDLES:]:
    if isinstance(candle, dict):
        ts_raw = candle.get("end_period_ts")
        price_obj = candle.get("price") or {}
        # Historical API returns price values as dollar strings (e.g. "0.5500" = 55¢)
        # Fall back to yes_bid OHLC if price is all None
        open_p = price_obj.get("open")
        high_p = price_obj.get("high")
        low_p  = price_obj.get("low")
        close_p = price_obj.get("close")
        if all(v is None for v in (open_p, high_p, low_p, close_p)):
            bid = candle.get("yes_bid") or {}
            open_p = bid.get("open"); high_p = bid.get("high")
            low_p  = bid.get("low");  close_p = bid.get("close")
        volume = candle.get("volume", "?")
    else:
        ts_raw = getattr(candle, "end_period_ts", None)
        price_obj = getattr(candle, "price", None)
        open_p  = getattr(price_obj, "open", None) if price_obj else None
        high_p  = getattr(price_obj, "high", None) if price_obj else None
        low_p   = getattr(price_obj, "low", None) if price_obj else None
        close_p = getattr(price_obj, "close", None) if price_obj else None
        volume  = getattr(candle, "volume", "?")

    ts_str = ""
    if ts_raw:
        dt = datetime.datetime.fromtimestamp(ts_raw, tz=datetime.timezone.utc)
        ts_str = dt.strftime("%Y-%m-%d")

    print(f"{ts_str:^12}  {_to_cents(open_p):>6}  {_to_cents(high_p):>6}  "
          f"{_to_cents(low_p):>6}  {_to_cents(close_p):>6}  {str(volume):>10}")

if not candles:
    print("No candles returned for this period/market.")

print(f"\nTotal candles: {len(candles)}")
print("Historical candlestick format mirrors live candlesticks: price.open/high/low/close in cents.")
