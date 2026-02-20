"""10_websocket/01_ws_ticker.py

Demonstrates: WebSocket `ticker` channel
- Streams L1 bid/ask updates for 3 open markets.
- Kalshi sends pings every ~10s; websockets library auto-responds with pong.
- Re-signs auth headers on every reconnect (stale timestamps are rejected).
- Press Ctrl+C to stop cleanly.

Run:
    uv run python 10_websocket/01_ws_ticker.py
"""

import asyncio
import json
import signal

import websockets

from auth.client import build_ws_headers, get_ws_url, raw_get

shutdown_event = asyncio.Event()


def dispatch(msg: dict) -> None:
    msg_type = msg.get("type", "")
    if msg_type == "subscribed":
        print(f"  [subscribed] channels={msg.get('params', {}).get('channels', [])}")
    elif msg_type == "ticker":
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", "?")
        yes_bid = data.get("yes_bid", "?")
        yes_ask = data.get("yes_ask", "?")
        last = data.get("last_price", "?")
        volume = data.get("volume", data.get("volume_24h", "?"))
        print(f"  TICK | {ticker:<35} bid={yes_bid:>3}¢  ask={yes_ask:>3}¢  last={last:>3}¢  vol={volume}")
    elif msg_type == "error":
        print(f"  [error] {msg}")
    # heartbeat / pong messages are handled by the websockets library automatically


async def connect_and_stream(tickers: list) -> None:
    ws_url = get_ws_url()
    backoff = 1

    while not shutdown_event.is_set():
        try:
            auth_headers = build_ws_headers()  # re-sign on every connect
            async with websockets.connect(
                ws_url, additional_headers=auth_headers, ping_interval=None
            ) as ws:
                backoff = 1
                subscribe = {
                    "id": 1,
                    "cmd": "subscribe",
                    "params": {"channels": ["ticker"], "market_tickers": tickers},
                }
                await ws.send(json.dumps(subscribe))
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

    # Fetch 3 open markets via raw HTTP (SDK pydantic fails on demo null fields)
    data = raw_get("/markets", status="open", limit=3)
    markets = data.get("markets", [])
    tickers = [m["ticker"] for m in markets if m.get("ticker")]

    if not tickers:
        print("No open markets found.")
        return

    print("=== WebSocket Ticker Stream ===")
    print(f"Markets: {tickers}")
    print("(Ctrl+C to stop)\n")

    await connect_and_stream(tickers)
    print("\nStreaming stopped.")


asyncio.run(main())
