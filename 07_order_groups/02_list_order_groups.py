"""07_order_groups/02_list_order_groups.py

Demonstrates: client.get_order_groups() and client.get_order_group(group_id=...)
- Lists all your order groups.
- Fetches per-group detail including linked order IDs.
- Requires credentials in .env

SDK method: get_order_groups()
SDK response type: GetOrderGroupsResponse
  .order_groups -> list[OrderGroup]
    OrderGroup fields: id, is_auto_cancel_enabled

SDK method: get_order_group(group_id: str)
SDK response type: GetOrderGroupResponse
  .is_auto_cancel_enabled -> bool
  .orders                 -> list (linked order IDs or Order objects)

Run:
    uv run python 07_order_groups/02_list_order_groups.py
"""

from auth.client import get_client

client = get_client()

print("=== Order Groups ===\n")

resp = client.get_order_groups()
groups = resp.order_groups or []

if not groups:
    print("No order groups found.")
    print("Run 07_order_groups/01_create_order_group.py to create one.")
else:
    print(f"Found {len(groups)} order group(s):\n")
    for g in groups:
        print(f"  Group ID : {g.id}")
        print(f"  Auto-cancel: {g.is_auto_cancel_enabled}")

        # Fetch per-group detail
        try:
            detail_resp = client.get_order_group(group_id=g.id)
            orders = detail_resp.orders or []
            print(f"  Orders   : {len(orders)} linked")
            for o in orders[:5]:
                if isinstance(o, str):
                    print(f"    order_id: {o}")
                else:
                    oid = getattr(o, "order_id", getattr(o, "id", str(o)))
                    print(f"    order_id: {oid}")
        except Exception as exc:
            print(f"  (detail fetch error: {exc})")
        print()
