"""04_portfolio/02_get_positions.py

Demonstrates: client.get_positions()
- Open positions in your portfolio.
- Requires credentials in .env

SDK method: get_positions(cursor, limit, count_filter, ticker, event_ticker)
SDK response type: GetPositionsResponse
  .market_positions -> list[MarketPosition]
  .event_positions  -> list[EventPosition]
  .cursor           -> str | None

MarketPosition fields:
  ticker, position (int: +yes, -no), total_traded, total_traded_dollars,
  market_exposure, market_exposure_dollars, realized_pnl, realized_pnl_dollars,
  resting_orders_count, fees_paid, fees_paid_dollars

Run:
    uv run python 04_portfolio/02_get_positions.py
"""

from auth.client import get_client

client = get_client()

print("=== Open Positions ===\n")
resp = client.get_positions(limit=20)
positions = resp.market_positions or []

if not positions:
    print("No open positions found.")
    print("Run one of the order scripts (05_orders/) to create some positions.")
else:
    print(f"{'Ticker':<35} {'Side':>5} {'Qty':>6} {'Exposure':>12} {'Realized P&L':>14}")
    print("-" * 78)
    for pos in positions:
        # position > 0 = net yes, < 0 = net no
        qty = abs(pos.position)
        side = "yes" if pos.position > 0 else "no"
        exposure_str = f"${pos.market_exposure_dollars:.4f}" if pos.market_exposure_dollars else "?"
        pnl_str = f"${pos.realized_pnl_dollars:.4f}" if pos.realized_pnl_dollars else "?"
        print(f"{pos.ticker:<35} {side:>5} {qty:>6} {exposure_str:>12} {pnl_str:>14}")

if resp.cursor:
    print(f"\nMore positions available (cursor: {resp.cursor!r})")

print(f"\nTotal market positions: {len(positions)}")
print("\nField notes:")
print("  position > 0 = net yes contracts held")
print("  position < 0 = net no contracts held")
print("  market_exposure = current dollar cost of position")
print("  realized_pnl    = profit/loss from closed portions")
