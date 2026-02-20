"""08_historical/04_historical_fills.py

Demonstrates: GET /historical/fills
- Fill history for trades made before the historical cutoff timestamp.
- Pre-cutoff fills are not returned by the standard GET /portfolio/fills endpoint.
- Requires credentials in .env

Run:
    uv run python 08_historical/04_historical_fills.py
"""

import datetime

from auth.client import get_client, raw_get

LIMIT = 20

client = get_client()

print("=== Historical Fills (pre-cutoff trades) ===\n")

# Try SDK method first, fall back to raw HTTP
fills = []
cursor = None
try:
    resp = client.get_historical_fills(limit=LIMIT)  # type: ignore[attr-defined]
    fills = list(getattr(resp, "fills", []) or [])
    cursor = getattr(resp, "cursor", None)
    print("(Used SDK method)\n")
except AttributeError:
    data = raw_get("/historical/fills", limit=LIMIT)
    fills = data.get("fills", [])
    cursor = data.get("cursor")
    print("(Used raw HTTP — SDK method not available)\n")

if not fills:
    print("No historical fills found.")
    print("Historical fills are trades made before the cutoff timestamp.")
    print("Run 08_historical/01_historical_cutoff.py to see when the cutoff is.")
else:
    print(f"{'Time':^22}  {'Ticker':<28}  {'Side':>5}  {'Price':>7}  {'Qty':>6}")
    print("-" * 75)
    for fill in fills:
        if isinstance(fill, dict):
            created = fill.get("created_time", fill.get("ts"))
            ticker = fill.get("market_id", fill.get("ticker", "?"))
            side = fill.get("side", fill.get("purchased_side", "?"))
            yes_price = fill.get("yes_price", "?")
            count = fill.get("count", "?")
        else:
            created = getattr(fill, "created_time", None)
            ticker = getattr(fill, "market_id", getattr(fill, "ticker", "?"))
            side = getattr(fill, "side", getattr(fill, "purchased_side", "?"))
            yes_price = getattr(fill, "yes_price", "?")
            count = getattr(fill, "count", "?")

        ts_str = ""
        if created:
            if isinstance(created, str):
                dt = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
            elif isinstance(created, (int, float)):
                dt = datetime.datetime.fromtimestamp(created, tz=datetime.timezone.utc)
            else:
                dt = created
            ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        print(f"{ts_str:^22}  {str(ticker):<28}  {str(side):>5}  {str(yes_price):>6}¢  {str(count):>6}")

if cursor:
    print(f"\nMore historical fills (cursor: {cursor!r})")

print(f"\nTotal fills shown: {len(fills)}")
print("\nFor fills after the cutoff, use 04_portfolio/03_get_fills.py instead.")
