"""10_websocket/04_ws_user_orders.py

Demonstrates: WebSocket `user_orders` channel (authenticated)
- Private stream of your own order lifecycle events.
- Events: order_created → resting → partially_filled → filled / canceled
- Shows order_id, status, remaining_count_fp for each event.
- Press Ctrl+C to stop.

Run:
    uv run python 10_websocket/04_ws_user_orders.py
"""

import asyncio
import json
import signal

import websockets

from auth.client import build_ws_headers, get_ws_url

shutdown_event = asyncio.Event()
event_count = 0


def dispatch(msg: dict) -> None:
    global event_count
    msg_type = msg.get("type", "")

    if msg_type == "subscribed":
        print(f"  [subscribed] {msg.get('params', {}).get('channels', [])}")
        print("  Listening for order events (place/cancel orders to see activity)...\n")

    elif msg_type in ("order_created", "order_updated", "user_orders"):
        event_count += 1
        data = msg.get("msg", {})
        order_id = str(data.get("order_id", data.get("id", "?")))[:16]
        ticker = data.get("ticker", data.get("market_id", "?"))
        status = data.get("status", "?")
        yes_price = data.get("yes_price", "?")
        remaining = data.get("remaining_count_fp", data.get("count_fp", "?"))
        filled = data.get("filled_count_fp", 0)

        print(
            f"  #{event_count:4d} | order_id={order_id}... | "
            f"{ticker:<30} | status={status:<18} | "
            f"remaining={remaining} | filled={filled} | price={yes_price}¢"
        )

    elif msg_type == "error":
        print(f"  [error] {msg}")


async def connect_and_stream() -> None:
    ws_url = get_ws_url()
    backoff = 1

    while not shutdown_event.is_set():
        try:
            auth_headers = build_ws_headers()
            async with websockets.connect(
                ws_url, additional_headers=auth_headers, ping_interval=None
            ) as ws:
                backoff = 1
                # user_orders does NOT require market_tickers — receives all your order events
                await ws.send(json.dumps({
                    "id": 1,
                    "cmd": "subscribe",
                    "params": {"channels": ["user_orders"]},
                }))
                async for raw in ws:
                    if shutdown_event.is_set():
                        break
                    dispatch(json.loads(raw))

        except (websockets.ConnectionClosed, OSError) as exc:
            if shutdown_event.is_set():
                break
            print(f"  [reconnect] {exc} — retrying in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


async def main() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    print("=== WebSocket User Orders Stream (private) ===")
    print("Subscribe: user_orders channel (all your orders — no market_tickers needed)")
    print("Tip: While this is running, create or cancel orders using the 05_orders/ scripts.")
    print("(Ctrl+C to stop)\n")

    await connect_and_stream()
    print(f"\nTotal order events received: {event_count}")


asyncio.run(main())
