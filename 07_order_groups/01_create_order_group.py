"""07_order_groups/01_create_order_group.py

Demonstrates: client.create_order_group(contracts_limit=...)
- Order groups contain orders and implement auto-cancel behavior.
- When is_auto_cancel_enabled=True: orders in the group can be auto-canceled.
- Requires credentials + demo env in .env

SDK method: create_order_group(**kwargs) → CreateOrderGroupRequest
CreateOrderGroupRequest fields:
  contracts_limit (int): max total contracts across all orders in the group

SDK response type: CreateOrderGroupResponse
  .order_group_id -> str

Run:
    uv run python 07_order_groups/01_create_order_group.py
"""

from auth.client import get_client

client = get_client()

print("=== Create Order Group ===\n")

print("Creating order group with contracts_limit=5 ...")
resp = client.create_order_group(contracts_limit=5)

print(f"\nOrder group created:")
print(f"  order_group_id: {resp.order_group_id}")

print(f"\nSet KALSHI_EXAMPLE_GROUP_ID={resp.order_group_id} in .env")
print("Then run 07_order_groups/03_order_with_group.py to add orders to this group.")
