"""05_orders/04_amend_order.py

Demonstrates: client.amend_order(order_id=..., ...)
- Amend is an atomic cancel + rebook at a new price.
- A new order_id is issued; the old order_id is canceled.
- Requires credentials + demo env in .env

SDK method: amend_order(order_id: str, **kwargs) → kwargs become AmendOrderRequest
AmendOrderRequest fields:
  ticker, side, action, count, yes_price (int), yes_price_dollars (str),
  client_order_id (original), updated_client_order_id (new)

Flow: Create 1¢ order → amend to 2¢ → print before/after order_id

Run:
    uv run python 05_orders/04_amend_order.py
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

print("=== Amend Order (atomic cancel + rebook) ===\n")

# Step 1: Create original order at 1¢
original_client_order_id = str(uuid.uuid4())
print(f"Step 1: Creating limit buy at 1¢ on {ticker} ...")
create_resp = client.create_order(
    ticker=ticker,
    side="yes",
    action="buy",
    type="limit",
    count=1,
    yes_price=1,
    client_order_id=original_client_order_id,
)
original = create_resp.order
print(f"  Created: order_id={original.order_id}  yes_price={original.yes_price}¢\n")

# Step 2: Amend to 2¢
# AmendOrderRequest requires BOTH client_order_id (original) and updated_client_order_id (new)
new_client_order_id = str(uuid.uuid4())
print("Step 2: Amending price to 2¢ ...")
amend_resp = client.amend_order(
    order_id=original.order_id,
    ticker=ticker,
    side="yes",
    action="buy",
    count=1,
    yes_price=2,
    client_order_id=original_client_order_id,       # required: original UUID
    updated_client_order_id=new_client_order_id,    # required: new UUID
)
amended = amend_resp.order
print(f"  Amended: order_id={amended.order_id}  yes_price={amended.yes_price}¢\n")

print("--- Before vs After ---")
print(f"  Original order_id: {original.order_id}  (now canceled)")
print(f"  New order_id     : {amended.order_id}  (resting at {amended.yes_price}¢)")
print()
print("Key insight:")
print("  amend_order is NOT an in-place update.")
print("  The old order is canceled and a new order is created at the new price.")
print("  The new order LOSES queue position (joins back of book at new price).")
print(f"\nClean up: cancel order_id {amended.order_id}")
