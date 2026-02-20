"""10_websocket/06_ws_market_lifecycle.py

Demonstrates: WebSocket `market_lifecycle_v2` channel
- Streams market state changes: open → closed → determined → settled.
- settlement_value is set when a market resolves (100 = YES won, 0 = NO won).
- This channel does NOT use market_tickers — it receives events for ALL markets.
- Press Ctrl+C to stop.

Run:
    uv run python 10_websocket/06_ws_market_lifecycle.py
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
        print("  Listening for market lifecycle events (may be infrequent)...\n")

    elif msg_type in ("market_lifecycle_v2", "market_lifecycle", "market_updated"):
        event_count += 1
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", data.get("ticker", "?"))
        status = data.get("status", "?")
        settlement_value = data.get("settlement_value", None)
        event_type = data.get("event_type", msg_type)

        line = (
            f"  #{event_count:4d} | [{event_type}] {ticker:<35} | "
            f"status={status}"
        )
        if settlement_value is not None:
            winner = "YES" if settlement_value == 100 else ("NO" if settlement_value == 0 else f"{settlement_value}¢")
            line += f" | settlement={settlement_value}¢ ({winner} won)"
        print(line)

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
                # market_lifecycle_v2 does NOT accept market_tickers — receives ALL markets
                await ws.send(json.dumps({
                    "id": 1,
                    "cmd": "subscribe",
                    "params": {"channels": ["market_lifecycle_v2"]},
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

    print("=== WebSocket Market Lifecycle Stream ===")
    print("Channel: market_lifecycle_v2")
    print("Note: This channel broadcasts changes for ALL markets — no market_tickers needed.")
    print("      Events may be infrequent between market open/close times.")
    print("\nMarket state transitions:")
    print("  open → closed → determined (settlement_value set) → settled")
    print("\n(Ctrl+C to stop)\n")

    await connect_and_stream()
    print(f"\nTotal lifecycle events received: {event_count}")


asyncio.run(main())
