"""10_websocket/03_ws_public_trades.py

Demonstrates: WebSocket `trade` channel
- Real-time public trade tape — every executed trade as it happens.
- Shows taker_side (the aggressing side that crossed the spread).
- Press Ctrl+C to stop.

Run:
    uv run python 10_websocket/03_ws_public_trades.py
"""

import asyncio
import json
import signal

import websockets

from auth.client import build_ws_headers, get_ws_url, raw_get

shutdown_event = asyncio.Event()
trade_count = 0


def dispatch(msg: dict) -> None:
    global trade_count
    msg_type = msg.get("type", "")

    if msg_type == "subscribed":
        print(f"  [subscribed] {msg.get('params', {}).get('channels', [])}")
        print("  Waiting for trades ...\n")

    elif msg_type == "trade":
        trade_count += 1
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", "?")
        yes_price = data.get("yes_price", "?")
        count_fp = data.get("count_fp", data.get("count", "?"))
        taker_side = data.get("taker_side", "?")
        trade_id = str(data.get("trade_id", data.get("id", "?")))[:12]

        contracts = count_fp // 100 if isinstance(count_fp, int) else count_fp

        print(
            f"  #{trade_count:4d} | {ticker:<35} | "
            f"price={yes_price:>3}¢ | qty={str(contracts):>4} | "
            f"taker={taker_side:>3} | id={trade_id}..."
        )

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
                await ws.send(json.dumps({
                    "id": 1,
                    "cmd": "subscribe",
                    "params": {"channels": ["trade"], "market_tickers": tickers},
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

    # Watch the 3 most active markets via raw HTTP
    data = raw_get("/markets", status="open", limit=20)
    markets = data.get("markets", [])
    markets_sorted = sorted(markets, key=lambda m: m.get("volume") or 0, reverse=True)
    tickers = [m["ticker"] for m in markets_sorted[:3] if m.get("ticker")]

    if not tickers:
        print("No open markets found.")
        return

    print("=== WebSocket Public Trade Stream ===")
    print(f"Watching: {tickers}")
    print("(Ctrl+C to stop)\n")

    await connect_and_stream(tickers)
    print(f"\nTotal trades received: {trade_count}")


asyncio.run(main())
