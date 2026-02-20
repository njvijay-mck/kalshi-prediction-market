"""07_order_groups/04_manage_order_group.py

Demonstrates: Order group lifecycle management
- Create → Reset → Delete
- Shows available SDK operations: create_order_group, reset_order_group, delete_order_group
- Requires credentials + demo env in .env

SDK methods:
  create_order_group(**kwargs)        → CreateOrderGroupResponse (.order_group_id)
  get_order_group(group_id: str)      → GetOrderGroupResponse (.is_auto_cancel_enabled, .orders)
  reset_order_group(group_id: str)    → (reset state)
  delete_order_group(group_id: str)   → (deleted)

Note: The SDK's OrderGroupsApi has: create, get, get_all, reset, delete
      There is no separate trigger action in the SDK — auto-cancel is system-managed.

Run:
    uv run python 07_order_groups/04_manage_order_group.py
"""

import time

from auth.client import get_client

client = get_client()

print("=== Order Group Lifecycle Management ===\n")

# Step 1: Create a group
print("Step 1: Create group (contracts_limit=5) ...")
create_resp = client.create_order_group(contracts_limit=5)
group_id = create_resp.order_group_id
print(f"  group_id={group_id}\n")

time.sleep(0.5)

# Step 2: Fetch group detail
print("Step 2: Get group detail ...")
try:
    detail_resp = client.get_order_group(group_id=group_id)
    print(f"  is_auto_cancel_enabled: {detail_resp.is_auto_cancel_enabled}")
    print(f"  linked orders         : {len(detail_resp.orders or [])}\n")
except Exception as exc:
    print(f"  Error: {exc}\n")

time.sleep(0.5)

# Step 3: Reset the group
print("Step 3: Reset group ...")
try:
    client.reset_order_group(group_id=group_id)
    print("  Reset successful.\n")
except Exception as exc:
    print(f"  Reset: {exc}\n")

time.sleep(0.5)

# Step 4: Delete the group
print(f"Step 4: Delete group {group_id} ...")
try:
    client.delete_order_group(group_id=group_id)
    print("  Deleted successfully.\n")
except Exception as exc:
    print(f"  Delete: {exc}\n")

# Verify deletion
print("Step 5: Verify deletion (should return error) ...")
try:
    client.get_order_group(group_id=group_id)
    print("  Still exists (unexpected).")
except Exception as exc:
    print(f"  Confirmed deleted: {type(exc).__name__}\n")

print("--- SDK Order Group Methods ---")
print("  create_order_group(contracts_limit=N)  → order_group_id")
print("  get_order_group(group_id)              → is_auto_cancel_enabled, orders")
print("  get_order_groups()                     → list[OrderGroup]")
print("  reset_order_group(group_id)            → reset state")
print("  delete_order_group(group_id)           → deleted")
