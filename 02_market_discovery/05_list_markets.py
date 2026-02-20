"""02_market_discovery/05_list_markets.py

Demonstrates: GET /markets (open markets list with filtering)
- Market listing with filtering.
- Highlights _dollars field naming convention (float alongside integer fields).
- Public endpoint: no credentials needed.

Note: Uses raw_get() instead of client.get_markets() because some demo markets
      return null for optional fields (category, risk_limit_cents) which causes
      pydantic validation errors in the SDK model.

Run:
    uv run python 02_market_discovery/05_list_markets.py
"""

from auth.client import raw_get

print("=== Open Markets (first 20) ===\n")

data = raw_get("/markets", status="open", limit=20)
markets = data.get("markets", [])
cursor = data.get("cursor")

print(f"{'Ticker':<35} {'yes_bid':>8} {'yes_ask':>8} {'volume':>10} {'open_int':>10}")
print("-" * 75)

for m in markets:
    ticker = m.get("ticker", "?")
    yes_bid = m.get("yes_bid")
    yes_ask = m.get("yes_ask")
    volume = m.get("volume", m.get("volume_24h"))
    open_interest = m.get("open_interest")

    bid_str = f"{yes_bid}¢" if yes_bid is not None else "?"
    ask_str = f"{yes_ask}¢" if yes_ask is not None else "?"
    print(f"{ticker:<35} {bid_str:>8} {ask_str:>8} {str(volume):>10} {str(open_interest):>10}")

print()
print(f"Total returned: {len(markets)}")
print(f"Next cursor   : {cursor!r}")

if markets:
    m = markets[0]
    print(f"\n--- Field naming for: {m.get('ticker')} ---")
    print(f"  yes_bid          : {m.get('yes_bid')}¢  (integer cents)")
    print(f"  yes_bid_dollars  : ${m.get('yes_bid_dollars')}  (string dollars)")
    print(f"  yes_ask          : {m.get('yes_ask')}¢")
    print(f"  yes_ask_dollars  : ${m.get('yes_ask_dollars')}")
    print(f"  last_price       : {m.get('last_price')}¢")

print("\nKey relationship: yes_bid + no_ask = 100 (always, in cents)")
