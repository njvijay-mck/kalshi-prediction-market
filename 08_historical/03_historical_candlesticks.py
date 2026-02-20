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
start_ts = int((now - datetime.timedelta(days=90)).timestamp())
end_ts = int(now.timestamp())

data = raw_get(
    f"/historical/markets/{ticker}/candlesticks",
    period_interval=PERIOD_INTERVAL,
    start_ts=start_ts,
    end_ts=end_ts,
)
candles = data.get("candlesticks", data.get("candles", []))

print(f"Ticker: {ticker}  |  period_interval={PERIOD_INTERVAL}m (daily)")
print(f"Date range: last 90 days\n")
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

for candle in candles[-MAX_CANDLES:]:
    if isinstance(candle, dict):
        ts_raw = candle.get("end_period_ts", candle.get("ts"))
        # Historical candles may have price as a nested dict with open/high/low/close
        price_obj = candle.get("price", candle)
        open_p = price_obj.get("open") if isinstance(price_obj, dict) else candle.get("open")
        high_p = price_obj.get("high") if isinstance(price_obj, dict) else candle.get("high")
        low_p = price_obj.get("low") if isinstance(price_obj, dict) else candle.get("low")
        close_p = price_obj.get("close") if isinstance(price_obj, dict) else candle.get("close")
        volume = candle.get("volume", "?")
    else:
        ts_raw = getattr(candle, "end_period_ts", None)
        price_obj = getattr(candle, "price", None)
        open_p = getattr(price_obj, "open", None) if price_obj else None
        high_p = getattr(price_obj, "high", None) if price_obj else None
        low_p = getattr(price_obj, "low", None) if price_obj else None
        close_p = getattr(price_obj, "close", None) if price_obj else None
        volume = getattr(candle, "volume", "?")

    ts_str = ""
    if ts_raw:
        dt = datetime.datetime.fromtimestamp(ts_raw, tz=datetime.timezone.utc)
        ts_str = dt.strftime("%Y-%m-%d")

    o = f"{open_p}¢" if open_p is not None else "?"
    h = f"{high_p}¢" if high_p is not None else "?"
    l = f"{low_p}¢" if low_p is not None else "?"
    c = f"{close_p}¢" if close_p is not None else "?"
    print(f"{ts_str:^12}  {o:>6}  {h:>6}  {l:>6}  {c:>6}  {str(volume):>10}")

if not candles:
    print("No candles returned for this period/market.")

print(f"\nTotal candles: {len(candles)}")
print("Historical candlestick format mirrors live candlesticks: price.open/high/low/close in cents.")
