"""02_market_discovery/06_get_market.py

Demonstrates: GET /markets/{ticker}
- Full market schema for a single market.
- Shows yes+no=100 price relationship.
- Public endpoint: no credentials needed.

Note: Uses raw_get() instead of client.get_market() because some demo markets
      return null for required SDK model fields.

Run:
    uv run python 02_market_discovery/06_get_market.py
"""

import os

from auth.client import raw_get

ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not ticker:
    data = raw_get("/markets", status="open", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets found — cannot continue.")
        raise SystemExit(1)
    ticker = markets[0]["ticker"]
    print(f"(No KALSHI_EXAMPLE_TICKER set — using: {ticker})\n")

print(f"=== Market Detail: {ticker} ===\n")
data = raw_get(f"/markets/{ticker}")
m = data.get("market", data)

# Identity
print("Identity:")
for field in ("ticker", "event_ticker", "title", "subtitle", "status", "market_type", "category"):
    print(f"  {field:20s}: {m.get(field)}")

# Prices — the yes+no=100 relationship
print("\nPrices (in cents):")
yes_bid = m.get("yes_bid")
yes_ask = m.get("yes_ask")
no_bid = m.get("no_bid")
no_ask = m.get("no_ask")
last_price = m.get("last_price")
print(f"  yes_bid  : {yes_bid}¢    yes_ask  : {yes_ask}¢")
print(f"  no_bid   : {no_bid}¢    no_ask   : {no_ask}¢")
print(f"  last_price: {last_price}¢")

if yes_bid is not None and no_ask is not None:
    print(f"\n  yes_bid ({yes_bid}) + no_ask ({no_ask}) = {yes_bid + no_ask} (should be 100)")

# Dollar fields
print("\nDollar-denominated fields:")
for field in ("yes_bid_dollars", "yes_ask_dollars", "last_price_dollars", "notional_value_dollars"):
    val = m.get(field)
    if val is not None:
        print(f"  {field:30s}: ${val}")

# Volume
print("\nVolume & Open Interest:")
print(f"  volume        : {m.get('volume')}")
print(f"  volume_24h    : {m.get('volume_24h')}")
print(f"  open_interest : {m.get('open_interest')}")

# Settlement
print("\nSettlement:")
print(f"  settlement_value: {m.get('settlement_value')}")
print(f"  close_time      : {m.get('close_time')}")
print(f"  expiration_time : {m.get('expiration_time')}")
