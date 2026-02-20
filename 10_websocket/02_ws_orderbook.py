"""10_websocket/02_ws_orderbook.py

Demonstrates: WebSocket `orderbook_delta` channel
- Maintains a local L2 order book state using snapshot + incremental deltas.
- Snapshot: replace local state entirely.
- Delta: apply delta_fp to existing qty; delete level if qty <= 0.
- Renders top-5 levels after each update.
- Press Ctrl+C to stop.

Run:
    uv run python 10_websocket/02_ws_orderbook.py
"""

import asyncio
import json
import os
import signal
from collections import defaultdict

import websockets

from auth.client import build_ws_headers, get_ws_url, raw_get

shutdown_event = asyncio.Event()

# Local state: ticker → side → price_str → qty
book: dict = defaultdict(lambda: defaultdict(dict))


def render_book(ticker: str) -> None:
    """Print top-5 yes bids for a market."""
    sides = book.get(ticker, {})
    yes_side = sides.get("yes", {})
    # Sort prices descending (best bid first)
    sorted_levels = sorted(
        ((float(p), qty) for p, qty in yes_side.items()),
        reverse=True,
    )
    print(f"\n  --- {ticker} (yes bids, top 5) ---")
    print(f"  {'Price':>8}  {'Qty':>8}")
    for price, qty in sorted_levels[:5]:
        print(f"  {price:>7.0f}¢  {qty:>8.0f}")
    if not sorted_levels:
        print("  (empty)")


def dispatch(msg: dict) -> None:
    msg_type = msg.get("type", "")

    if msg_type == "subscribed":
        print(f"  [subscribed] {msg.get('params', {}).get('channels', [])}")

    elif msg_type == "orderbook_snapshot":
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", "?")
        book[ticker] = defaultdict(dict)  # reset
        for side in ("yes", "no"):
            for entry in data.get(side, []):
                if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    price_str = str(entry[0])
                    book[ticker][side][price_str] = float(entry[1])
        print(f"  [snapshot] {ticker} — {sum(len(v) for v in book[ticker].values())} price levels")
        render_book(ticker)

    elif msg_type == "orderbook_delta":
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", "?")
        side = data.get("side", "yes")
        price = str(data.get("price", "?"))
        delta_fp = float(data.get("delta_fp", data.get("delta", 0)))

        current = book[ticker][side].get(price, 0.0)
        new_qty = current + delta_fp

        if new_qty <= 0:
            book[ticker][side].pop(price, None)
        else:
            book[ticker][side][price] = new_qty

        render_book(ticker)

    elif msg_type == "error":
        print(f"  [error] {msg}")


async def connect_and_stream(tickers: list) -> None:
    ws_url = get_ws_url()
    backoff = 1

    while not shutdown_event.is_set():
        try:
            auth_headers = build_ws_headers()
            async with websockets.connect(
                ws_url, additional_headers=auth_headers, ping_interval=None
            ) as ws:
                backoff = 1
                # Clear local book on (re)connect to start fresh with new snapshot
                book.clear()
                await ws.send(json.dumps({
                    "id": 1,
                    "cmd": "subscribe",
                    "params": {"channels": ["orderbook_delta"], "market_tickers": tickers},
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

    ticker = os.getenv("KALSHI_EXAMPLE_TICKER", "")
    if not ticker:
        data = raw_get("/markets", status="open", limit=1)
        markets = data.get("markets", [])
        if not markets:
            print("No open markets found.")
            return
        ticker = markets[0]["ticker"]

    print("=== WebSocket Order Book (L2 real-time) ===")
    print(f"Market: {ticker}")
    print("(Ctrl+C to stop)\n")

    await connect_and_stream([ticker])
    print("\nStreaming stopped.")


asyncio.run(main())
