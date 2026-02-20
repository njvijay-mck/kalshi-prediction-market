"""06_batch_operations/01_batch_create_orders.py

Demonstrates: client.batch_create_orders(orders=[...])
- Submit multiple limit orders in a single API call (1 write unit total).
- Partial fill semantics: some orders may succeed even if others fail.
- Requires credentials + demo env in .env

SDK method: batch_create_orders(**kwargs) → BatchCreateOrdersRequest
BatchCreateOrdersRequest fields:
  orders: list[CreateOrderRequest]

SDK response type: BatchCreateOrdersResponse
  .orders -> list[BatchCreateOrdersIndividualResponse]
    BatchCreateOrdersIndividualResponse: order, error (if any)

Run:
    uv run python 06_batch_operations/01_batch_create_orders.py
"""

import uuid

from auth.client import get_client, raw_get
from kalshi_python_sync import CreateOrderRequest

client = get_client()

# Find 2 different open markets
data = raw_get("/markets", status="open", limit=5)
markets = data.get("markets", [])
if len(markets) < 2:
    print("Need at least 2 open markets — cannot continue.")
    raise SystemExit(1)

ticker1 = markets[0]["ticker"]
ticker2 = markets[1]["ticker"]

order1 = CreateOrderRequest(
    ticker=ticker1,
    side="yes",
    action="buy",
    type="limit",
    count=1,
    yes_price=1,
    client_order_id=str(uuid.uuid4()),
)
order2 = CreateOrderRequest(
    ticker=ticker2,
    side="yes",
    action="buy",
    type="limit",
    count=1,
    yes_price=1,
    client_order_id=str(uuid.uuid4()),
)

print("=== Batch Create Orders ===\n")
print("Submitting 2 orders in one API call:")
print(f"  Order 1: {ticker1}  yes buy  1¢  count=1")
print(f"  Order 2: {ticker2}  yes buy  1¢  count=1")
print()

batch_resp = client.batch_create_orders(orders=[order1, order2])
results = batch_resp.orders or []

print("Results:")
for result in results:
    order = getattr(result, "order", None)
    error = getattr(result, "error", None)
    if error:
        print(f"  FAILED: {error}")
    elif order:
        print(f"  OK: order_id={order.order_id}  ticker={order.ticker}  status={order.status}")
    else:
        print(f"  Response: {result}")

print("\nKey concepts:")
print("  1 write unit for the entire batch (vs N write units for N individual calls)")
print("  Partial success: some orders may fail while others succeed")
print("  Each order still has its own client_order_id for idempotency")
print("\nRun 06_batch_operations/02_batch_cancel_orders.py to cancel these orders.")
