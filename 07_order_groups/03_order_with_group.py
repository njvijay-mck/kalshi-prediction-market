"""07_order_groups/03_order_with_group.py

Demonstrates: creating an order with order_group_id field
- Assigns the order to an existing group at creation time.
- Requires credentials + demo env in .env
- Set KALSHI_EXAMPLE_GROUP_ID in .env (from 01_create_order_group.py output)

Run:
    KALSHI_EXAMPLE_GROUP_ID=<group-id> uv run python 07_order_groups/03_order_with_group.py
"""

import os
import uuid

from auth.client import get_client, raw_get

client = get_client()

group_id = os.getenv("KALSHI_EXAMPLE_GROUP_ID", "")
if not group_id:
    print("No KALSHI_EXAMPLE_GROUP_ID set.")
    print("Run 07_order_groups/01_create_order_group.py first.\n")
    print("Creating a new group for this demo ...")
    create_group_resp = client.create_order_group(contracts_limit=5)
    group_id = create_group_resp.order_group_id
    print(f"  Created group: {group_id}\n")

ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
if not ticker:
    data = raw_get("/markets", status="open", limit=1)
    markets = data.get("markets", [])
    if not markets:
        print("No open markets — cannot continue.")
        raise SystemExit(1)
    ticker = markets[0]["ticker"]

print(f"=== Create Order with Group Assignment ===\n")
print(f"  ticker        : {ticker}")
print(f"  order_group_id: {group_id}")
print(f"  count         : 1 contract")
print(f"  yes_price     : 1¢\n")

resp = client.create_order(
    ticker=ticker,
    side="yes",
    action="buy",
    type="limit",
    count=1,
    yes_price=1,
    client_order_id=str(uuid.uuid4()),
    order_group_id=group_id,   # <-- assigns this order to the group
)
order = resp.order

print("Order created:")
print(f"  order_id      : {order.order_id}")
print(f"  status        : {order.status}")
print(f"  order_group_id: {order.order_group_id}")
print("\nThis order now belongs to the group.")
print(f"\nClean up: cancel order {order.order_id}")
