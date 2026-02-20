"""05_orders/07_order_queue_position.py

Demonstrates:
  - client.get_order_queue_position(order_id=...) — single order
  - client.get_order_queue_positions(market_tickers=...) — all resting orders in a market

Position 1 = next in line to be filled at that price level.
Requires credentials + demo env in .env

SDK response types:
  GetOrderQueuePositionResponse  -> .queue_position -> int
  GetOrderQueuePositionsResponse -> .queue_positions -> list[OrderQueuePosition]
    OrderQueuePosition: order_id, market_ticker, queue_position

Run:
    uv run python 05_orders/07_order_queue_position.py
"""

import os
import uuid

from auth.client import get_client, raw_get

client = get_client()

ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not ticker:
    data = raw_get("/markets", status="open", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets — cannot continue.")
        raise SystemExit(1)
    ticker = markets[0]["ticker"]

print("=== Order Queue Positions ===\n")

# Create a test order to inspect
print(f"Creating a 1¢ resting order on {ticker} ...")
create_resp = client.create_order(
    ticker=ticker,
    side="yes",
    action="buy",
    type="limit",
    count=1,
    yes_price=1,
    client_order_id=str(uuid.uuid4()),
)
order_id = create_resp.order.order_id
print(f"  Created: {order_id}\n")

# Single order queue position
print(f"Single order queue position for {order_id}:")
try:
    pos_resp = client.get_order_queue_position(order_id=order_id)
    print(f"  queue_position: {pos_resp.queue_position}")
    print("  (Position 1 = next to fill at this price level)")
except Exception as exc:
    print(f"  Error: {exc}")

# Bulk: all resting orders in a market
print(f"\nAll resting order positions in {ticker}:")
try:
    bulk_resp = client.get_order_queue_positions(market_tickers=[ticker])
    positions = getattr(bulk_resp, "queue_positions", getattr(bulk_resp, "order_queue_positions", [])) or []
    if positions:
        print(f"  {'Order ID':<40} {'Queue Position':>15}")
        print("  " + "-" * 57)
        for p in positions:
            print(f"  {p.order_id:<40} {str(p.queue_position):>15}")
    else:
        print("  No resting order positions returned.")
except Exception as exc:
    print(f"  Error: {exc}")

# Clean up
print(f"\nCleaning up test order {order_id} ...")
try:
    client.cancel_order(order_id=order_id)
    print("  Canceled.")
except Exception as exc:
    print(f"  Could not cancel: {exc}")
