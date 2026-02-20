"""03_market_data/01_get_orderbook.py

Demonstrates: GET /markets/{ticker}/orderbook?depth=5
- L2 order book for a single market.
- Kalshi stores only yes-side bids; no asks are implied (no_ask = 100 - yes_bid).
- Public endpoint: no credentials needed.

API response structure:
  orderbook.yes : list of [price, qty] pairs for yes side (bids)
  orderbook.no  : list of [price, qty] pairs for no side (bids)

Note: Uses raw_get() because the SDK Orderbook model uses var_true/var_false
      which may not deserialize cleanly on all demo data.

Run:
    uv run python 03_market_data/01_get_orderbook.py
"""

import os

from auth.client import raw_get

DEPTH = 5

ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not ticker:
    data = raw_get("/markets", status="open", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets found — cannot continue.")
        raise SystemExit(1)
    ticker = markets[0]["ticker"]
    print(f"(No KALSHI_EXAMPLE_TICKER set — using: {ticker})\n")

print(f"=== Order Book: {ticker} (depth={DEPTH}) ===\n")
data = raw_get(f"/markets/{ticker}/orderbook", depth=DEPTH)
book = data.get("orderbook", {})

# 'yes' = yes bids, 'no' = no bids; each is a list of [price, qty] pairs
yes_bids = book.get("yes") or []
no_bids = book.get("no") or []

print(f"{'YES bids':^30}   {'Implied NO asks':^30}")
print(f"{'Price':>8}  {'Qty':>8}   {'Price':>8}  {'Qty':>8}")
print("-" * 62)

for entry in yes_bids[:DEPTH]:
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        price, qty = entry[0], entry[1]
        no_price = 100 - price  # implied no ask
        print(f"{price:>7}¢  {qty:>8}   {no_price:>7}¢  {qty:>8}")

if not yes_bids:
    print("  (empty yes book)")

if no_bids:
    print("\nNo-side bids:")
    for entry in no_bids[:DEPTH]:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            price, qty = entry[0], entry[1]
            print(f"  no_bid: {price}¢  qty: {qty}")

print("\nKey insight:")
print("  Only yes-side bids are stored. Kalshi is a unified book.")
print("  To buy 'no' at 40¢, you sell 'yes' at 60¢ (= 100 - 40).")
print("  Book structure: yes=[price, qty] pairs sorted by price desc")
