"""05_orders/03_list_orders.py

Demonstrates: client.get_orders(status=..., limit=...)
- Filter by order status; shows cursor pagination.
- Requires credentials in .env

SDK method: get_orders(status, limit, cursor, ticker, min_ts, max_ts, ...)
SDK response type: GetOrdersResponse
  .orders -> list[Order]
  .cursor -> str | None

Order status values: 'resting', 'filled', 'canceled'

Run:
    uv run python 05_orders/03_list_orders.py
"""

from auth.client import get_client

LIMIT = 10

client = get_client()

print("=== Order List (by status) ===\n")

for status in ("resting", "filled", "canceled"):
    print(f"--- Status: {status} (limit={LIMIT}) ---")
    resp = client.get_orders(status=status, limit=LIMIT)
    orders = resp.orders or []
    cursor = resp.cursor

    if not orders:
        print(f"  No {status} orders found.")
    else:
        print(f"  {'Order ID':<40} {'Ticker':<30} {'Price':>7} {'Remaining':>10}")
        print("  " + "-" * 90)
        for o in orders:
            print(
                f"  {o.order_id:<40} {o.ticker:<30} "
                f"{str(o.yes_price):>6}¢ {str(o.remaining_count):>10}"
            )

    if cursor:
        print(f"  (more available, cursor: {cursor!r})")
    print()

print("Cursor pagination pattern:")
print("  cursor = None")
print("  while True:")
print("      resp = client.get_orders(status='resting', limit=200, cursor=cursor)")
print("      for o in resp.orders: process(o)")
print("      if not resp.cursor: break")
print("      cursor = resp.cursor")
