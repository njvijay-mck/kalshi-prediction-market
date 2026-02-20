"""06_batch_operations/02_batch_cancel_orders.py

Demonstrates: client.batch_cancel_orders(ids=[...])
- Cancel multiple resting orders in bulk.
- Each cancel costs 0.2 write units (vs 1.0 for single cancel).
- Requires credentials + demo env in .env

SDK method: batch_cancel_orders(**kwargs) → BatchCancelOrdersRequest
BatchCancelOrdersRequest fields:
  ids: list[str]  (order IDs to cancel)

SDK response type: BatchCancelOrdersResponse
  .orders -> list[BatchCancelOrdersIndividualResponse]

Run:
    uv run python 06_batch_operations/02_batch_cancel_orders.py
"""

import uuid

from auth.client import get_client, raw_get

client = get_client()

print("=== Batch Cancel Orders ===\n")

# Get all resting orders
resting_resp = client.get_orders(status="resting", limit=50)
resting_orders = resting_resp.orders or []
order_ids = [o.order_id for o in resting_orders]

if not order_ids:
    # Create some orders to cancel
    print("No resting orders found — creating 3 orders to demonstrate batch cancel...\n")
    data = raw_get("/markets", status="open", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets — cannot continue.")
        raise SystemExit(1)
    ticker = markets[0]["ticker"]

    for _ in range(3):
        cr = client.create_order(
            ticker=ticker,
            side="yes",
            action="buy",
            type="limit",
            count=1,
            yes_price=1,
            client_order_id=str(uuid.uuid4()),
        )
        order_ids.append(cr.order.order_id)
        print(f"  Created: {cr.order.order_id}")
    print()

print(f"Canceling {len(order_ids)} orders in one batch call:")
for oid in order_ids:
    print(f"  {oid}")
print()

batch_resp = client.batch_cancel_orders(ids=order_ids)
results = getattr(batch_resp, "orders", []) or []

if results:
    print("Results:")
    for result in results:
        order = getattr(result, "order", None)
        error = getattr(result, "error", None)
        if error:
            oid = getattr(order, "order_id", "?") if order else "?"
            print(f"  {oid}: FAILED — {error}")
        elif order:
            print(f"  {order.order_id}: {order.status}")
        else:
            print(f"  {result}")
else:
    print("Batch cancel submitted.")

n = len(order_ids)
print(f"\nRate limit cost comparison:")
print(f"  {n} individual cancels: {n * 1.0:.1f} write units")
print(f"  1 batch cancel call  : {n * 0.2:.1f} write units  ({20:.0f}% of individual cost)")
