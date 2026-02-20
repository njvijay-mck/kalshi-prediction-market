"""05_orders/06_cancel_order.py

Demonstrates: client.cancel_order(order_id=...)
- Cancels a resting order; handles common error cases gracefully.
- Requires credentials + demo env in .env

SDK method: cancel_order(order_id: str)
SDK response type: CancelOrderResponse -> .order -> Order

Run:
    uv run python 05_orders/06_cancel_order.py
    KALSHI_EXAMPLE_ORDER_ID=<id> uv run python 05_orders/06_cancel_order.py
"""

import os
import uuid

from auth.client import get_client, raw_get

client = get_client()

order_id = os.getenv("KALSHI_EXAMPLE_ORDER_ID", "")
if not order_id:
    # Create a fresh order to cancel
    ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
    if not ticker:
        data = raw_get("/markets", status="open", limit=1)
        markets = data.get("markets", [])
        if not markets:
            print("No open markets — cannot continue.")
            raise SystemExit(1)
        ticker = markets[0]["ticker"]

    print(f"(No KALSHI_EXAMPLE_ORDER_ID — creating a 1¢ order on {ticker} to cancel)\n")
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
    print(f"  Created order: {order_id}\n")

print(f"=== Cancel Order: {order_id} ===\n")

try:
    resp = client.cancel_order(order_id=order_id)
    order = resp.order
    print(f"  Result: order status = {order.status}")
    print("\nOrder canceled successfully.")
except Exception as exc:
    err_str = str(exc)
    if any(code in err_str for code in ("400", "404", "already", "filled")):
        print(f"  Could not cancel: {exc}")
        print("\nCommon reasons:")
        print("  - Order already filled (status='filled')")
        print("  - Order already canceled (status='canceled')")
        print("  - Order not found (wrong order_id or belongs to different account)")
    else:
        print(f"  Unexpected error: {exc}")
        raise

# Verify final status
try:
    get_resp = client.get_order(order_id=order_id)
    print(f"\nFinal order status: {get_resp.order.status}")
except Exception:
    pass

print("\nNote: Canceling an already-filled or already-canceled order returns an error.")
print("Always check order status before attempting to cancel.")
