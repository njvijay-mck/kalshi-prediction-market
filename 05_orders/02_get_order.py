"""05_orders/02_get_order.py

Demonstrates: client.get_order(order_id=...)
- Fetch a single order by ID — shows all status fields.
- Requires credentials in .env

SDK method: get_order(order_id: str)
SDK response type: GetOrderResponse -> .order -> Order

Order fields:
  order_id, user_id, client_order_id, ticker, side, action, type, status,
  yes_price, no_price, yes_price_dollars, no_price_dollars,
  fill_count, remaining_count, initial_count,
  taker_fees, maker_fees, queue_position,
  expiration_time, created_time, last_update_time

Run:
    uv run python 05_orders/02_get_order.py
"""

import os
import uuid

from auth.client import get_client, raw_get

client = get_client()

order_id = os.getenv("KALSHI_EXAMPLE_ORDER_ID", "")
if not order_id:
    # Create a temporary order to demonstrate
    ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
    if not ticker:
        data = raw_get("/markets", status="open", limit=1)
        markets = data.get("markets", [])
        if not markets:
            print("No open markets — cannot continue.")
            raise SystemExit(1)
        ticker = markets[0]["ticker"]

    print(f"(No order_id — creating a 1¢ order on {ticker} to demonstrate)\n")
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

print(f"=== Get Order: {order_id} ===\n")
resp = client.get_order(order_id=order_id)
order = resp.order

print("Core fields:")
print(f"  order_id         : {order.order_id}")
print(f"  ticker           : {order.ticker}")
print(f"  side             : {order.side}")
print(f"  action           : {order.action}")
print(f"  type             : {order.type}")
print(f"  status           : {order.status}")

print("\nPrice fields:")
print(f"  yes_price        : {order.yes_price}¢")
print(f"  yes_price_dollars: ${order.yes_price_dollars}")

print("\nCount fields:")
print(f"  initial_count    : {order.initial_count}")
print(f"  fill_count       : {order.fill_count}")
print(f"  remaining_count  : {order.remaining_count}")

print("\nFee fields:")
print(f"  taker_fees       : {order.taker_fees}")
print(f"  maker_fees       : {order.maker_fees}")
print(f"  queue_position   : {order.queue_position}")

print("\nTimestamps:")
print(f"  created_time     : {order.created_time}")
print(f"  last_update_time : {order.last_update_time}")
print(f"  expiration_time  : {order.expiration_time}")

print("\nStatus lifecycle:")
print("  pending → resting → (partially filled →) filled / canceled")
