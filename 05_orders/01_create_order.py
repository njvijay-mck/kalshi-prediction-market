"""05_orders/01_create_order.py

Demonstrates: client.create_order(...)
- Places a limit buy order at 1¢ (will not fill — safe for demo testing).
- Uses client_order_id (UUID) for idempotency: safe to re-run if it times out.
- Requires credentials + KALSHI_ENV=demo in .env

SDK method: create_order(**kwargs) — kwargs become a CreateOrderRequest
CreateOrderRequest fields:
  ticker (str), side (str), action (str), count (int), type (str),
  yes_price (int 1-99) OR yes_price_dollars (str "0.0100"),
  client_order_id (str, optional)

IMPORTANT: This places a real order in the demo environment.
           Run 05_orders/06_cancel_order.py afterwards to clean up.

Run:
    uv run python 05_orders/01_create_order.py
"""

import os
import uuid

from auth.client import get_client, raw_get

client_order_id = str(uuid.uuid4())

client = get_client()

ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not ticker:
    data = raw_get("/markets", status="open", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets found — cannot create order.")
        raise SystemExit(1)
    ticker = markets[0]["ticker"]
    print(f"(Using market: {ticker})\n")

print("=== Create Order ===\n")
print(f"  ticker          : {ticker}")
print(f"  side            : yes")
print(f"  action          : buy")
print(f"  type            : limit")
print(f"  count           : 1  (1 contract)")
print(f"  yes_price       : 1  (1¢ — will not fill)")
print(f"  client_order_id : {client_order_id}")
print()

resp = client.create_order(
    ticker=ticker,
    side="yes",
    action="buy",
    type="limit",
    count=1,        # 1 contract (integer, not fp)
    yes_price=1,    # 1¢ — safe: won't fill unless market is at rock bottom
    client_order_id=client_order_id,
)
order = resp.order

print("Order created successfully!")
print(f"  order_id          : {order.order_id}")
print(f"  status            : {order.status}")
print(f"  yes_price         : {order.yes_price}¢")
print(f"  yes_price_dollars : ${order.yes_price_dollars}")
print(f"  remaining_count   : {order.remaining_count}")
print(f"  created_time      : {order.created_time}")

print("\n--- Save this for subsequent scripts ---")
print(f"ORDER_ID={order.order_id}")

print("\nKey concepts:")
print("  count=1 → 1 contract (simple integer, not fractional pennies)")
print("  yes_price=1 → 1 cent (integer 1-99)")
print("  client_order_id → idempotency: re-run safely, server deduplicates")
print("  status='resting' → in the book, waiting for a match")
print("\nRun 05_orders/06_cancel_order.py to clean up this order.")
