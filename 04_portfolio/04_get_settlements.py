"""04_portfolio/04_get_settlements.py

Demonstrates: client.get_settlements(limit=20)
- Settled market payouts — markets that have resolved.
- Requires credentials in .env

SDK method: get_settlements(limit, cursor)
SDK response type: GetSettlementsResponse
  .settlements -> list[Settlement]
  .cursor      -> str | None

Settlement fields:
  ticker, event_ticker, market_result, yes_count, yes_total_cost,
  no_count, no_total_cost, revenue, settled_time, fee_cost, value

Run:
    uv run python 04_portfolio/04_get_settlements.py
"""

import datetime

from auth.client import get_client

LIMIT = 20

client = get_client()

print("=== Settlement History ===\n")
resp = client.get_settlements(limit=LIMIT)
settlements = resp.settlements or []

if not settlements:
    print("No settlements found.")
    print("Settlements appear after a market closes and resolves.")
    print("In demo env, some markets settle daily — check back later.")
else:
    print(
        f"{'Settled Time':^22}  {'Ticker':<28}  {'Result':>8}  {'Revenue':>10}"
    )
    print("-" * 76)
    for s in settlements:
        ts_str = ""
        if s.settled_time:
            if isinstance(s.settled_time, str):
                dt = datetime.datetime.fromisoformat(s.settled_time.replace("Z", "+00:00"))
            elif isinstance(s.settled_time, (int, float)):
                dt = datetime.datetime.fromtimestamp(s.settled_time, tz=datetime.timezone.utc)
            else:
                dt = s.settled_time
            ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        revenue_str = f"${s.revenue / 100:.4f}" if s.revenue is not None else "?"
        print(
            f"{ts_str:^22}  {s.ticker:<28}  {str(s.market_result):>8}  {revenue_str:>10}"
        )

if resp.cursor:
    print(f"\nMore settlements (cursor: {resp.cursor!r})")

print(f"\nTotal settlements shown: {len(settlements)}")
print("\nField notes:")
print("  market_result: 'yes' or 'no' — which side won")
print("  value        : settlement price in cents (100 = yes won, 0 = no won)")
print("  revenue      : your net payout in cents")
print("  positive revenue → you profited, negative → you lost")
