"""02_market_discovery/02_get_series.py

Demonstrates: GET /series/{series_ticker}
- Fetch detail for a single series by ticker.
- Public endpoint: no credentials needed.

Note: Uses raw_get() to avoid SDK pydantic validation issues on demo data.

Run:
    uv run python 02_market_discovery/02_get_series.py
"""

import os

from auth.client import raw_get

series_ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not series_ticker:
    data = raw_get("/series")
    series_list = data.get("series", [])
    if not series_list:
        print("No series available — cannot continue.")
        raise SystemExit(1)
    series_ticker = series_list[0]["ticker"]
    print(f"(No KALSHI_EXAMPLE_TICKER set — using first: {series_ticker})\n")

print(f"=== Series Detail: {series_ticker} ===\n")
data = raw_get(f"/series/{series_ticker}")
series = data.get("series", data)

for field in ("ticker", "title", "category", "frequency", "tags", "fee_type", "fee_multiplier"):
    print(f"  {field:20s}: {series.get(field)}")
