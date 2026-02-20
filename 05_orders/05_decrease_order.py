"""05_orders/05_decrease_order.py

Demonstrates: client.decrease_order(order_id=..., reduce_by=...)
- Decrease a resting order's quantity.
- Unlike amend, decrease KEEPS queue position.
- Requires credentials + demo env in .env

SDK method: decrease_order(order_id: str, **kwargs) → kwargs become DecreaseOrderRequest
DecreaseOrderRequest fields:
  reduce_by (int) : reduce quantity by this many contracts
  reduce_to (int) : reduce quantity to this many contracts (alternative)

Flow: Create 5-contract order → decrease by 3 → show before/after count

Run:
    uv run python 05_orders/05_decrease_order.py
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

print("=== Decrease Order (partial size reduction) ===\n")

INITIAL_CONTRACTS = 5
REDUCE_BY = 3

# Step 1: Create 5-contract order
print(f"Step 1: Creating {INITIAL_CONTRACTS}-contract limit buy at 1¢ on {ticker} ...")
create_resp = client.create_order(
    ticker=ticker,
    side="yes",
    action="buy",
    type="limit",
    count=INITIAL_CONTRACTS,
    yes_price=1,
    client_order_id=str(uuid.uuid4()),
)
order = create_resp.order
print(f"  Created: order_id={order.order_id}  initial_count={order.initial_count}  remaining_count={order.remaining_count}\n")

# Step 2: Decrease by 3 contracts
print(f"Step 2: Decreasing by {REDUCE_BY} contracts ...")
decrease_resp = client.decrease_order(
    order_id=order.order_id,
    reduce_by=REDUCE_BY,
)
updated = decrease_resp.order
print(f"  Updated: remaining_count={updated.remaining_count}\n")

print("--- Before vs After ---")
print(f"  Initial  : {INITIAL_CONTRACTS} contracts (initial_count={order.initial_count})")
print(f"  Reduced by: {REDUCE_BY} contracts")
print(f"  Remaining: {updated.remaining_count} contracts (expected {INITIAL_CONTRACTS - REDUCE_BY})")
print()
print("Key difference from amend:")
print("  decrease_order reduces qty WITHOUT canceling and rebooking.")
print("  The order KEEPS its position in the time-priority queue.")
print(f"\nClean up: cancel order_id {order.order_id}")
