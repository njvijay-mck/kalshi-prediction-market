"""10_websocket/05_ws_user_fills.py

Demonstrates: WebSocket `fill` channel (authenticated)
- Private stream of your own fill events — each time one of your orders executes.
- Shows count_fp, yes_price, fee_cost, and order_id for each fill.
- Press Ctrl+C to stop.

Run:
    uv run python 10_websocket/05_ws_user_fills.py
"""

import asyncio
import json
import signal

import websockets

from auth.client import build_ws_headers, get_ws_url

shutdown_event = asyncio.Event()
fill_count = 0
total_fee_fp = 0


def dispatch(msg: dict) -> None:
    global fill_count, total_fee_fp
    msg_type = msg.get("type", "")

    if msg_type == "subscribed":
        print(f"  [subscribed] {msg.get('params', {}).get('channels', [])}")
        print("  Listening for fills (place limit orders to see activity)...\n")

    elif msg_type == "fill":
        fill_count += 1
        data = msg.get("msg", {})
        order_id = str(data.get("order_id", "?"))[:16]
        ticker = data.get("market_id", data.get("ticker", "?"))
        yes_price = data.get("yes_price", "?")
        count_fp = data.get("count_fp", data.get("count", "?"))
        fee_cost = data.get("fee_cost", 0)
        purchased_side = data.get("side", data.get("purchased_side", "?"))
        action = data.get("action", "buy")

        if isinstance(fee_cost, (int, float)):
            total_fee_fp += fee_cost
            fee_str = f"${fee_cost/100:.4f}"
        else:
            fee_str = str(fee_cost)

        contracts = count_fp // 100 if isinstance(count_fp, int) else count_fp

        print(
            f"  #{fill_count:4d} | order={order_id}... | "
            f"{ticker:<28} | {purchased_side:>3} {action:>4} | "
            f"price={yes_price:>3}¢ | qty={str(contracts):>4} | fee={fee_str}"
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
                # 'fill' channel: receives your private fills across all markets
                await ws.send(json.dumps({
                    "id": 1,
                    "cmd": "subscribe",
                    "params": {"channels": ["fill"]},
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

    print("=== WebSocket User Fill Stream (private) ===")
    print("Subscribe: fill channel (your fills across all markets)")
    print("Tip: Place a limit order at the current ask price to get a fill quickly.")
    print("(Ctrl+C to stop)\n")

    await connect_and_stream()
    print(f"\nTotal fills received: {fill_count}")
    if fill_count > 0:
        print(f"Total fees paid: ${total_fee_fp/100:.4f}")
