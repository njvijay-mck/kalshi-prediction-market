"""08_historical/02_historical_markets.py

Demonstrates: GET /historical/markets
- Browse settled markets not available in the standard GET /markets endpoint.
- Markets here have already resolved (settlement_value is set).
- Requires credentials in .env

Run:
    uv run python 08_historical/02_historical_markets.py
"""

from auth.client import get_client, raw_get

LIMIT = 10

client = get_client()

print("=== Historical Markets (settled) ===\n")

# Try SDK method first, fall back to raw HTTP
markets = []
cursor = None
try:
    resp = client.get_historical_markets(limit=LIMIT)  # type: ignore[attr-defined]
    markets = list(getattr(resp, "markets", []) or [])
    cursor = getattr(resp, "cursor", None)
    print("(Used SDK method)\n")
except AttributeError:
    data = raw_get("/historical/markets", limit=LIMIT)
    markets = data.get("markets", [])
    cursor = data.get("cursor")
    print("(Used raw HTTP — SDK method not available)\n")

if not markets:
    print("No historical markets returned.")
else:
    print(f"{'Ticker':<35} {'Status':>10} {'Settlement':>12} {'Settled Time':^22}")
    print("-" * 82)
    for m in markets:
        if isinstance(m, dict):
            ticker = m.get("ticker", "?")
            status = m.get("status", "?")
            sv = m.get("settlement_value", "?")
            st = m.get("settled_time", m.get("settlement_time", "?"))
        else:
            ticker = getattr(m, "ticker", "?")
            status = getattr(m, "status", "?")
            sv = getattr(m, "settlement_value", "?")
            st = getattr(m, "settled_time", getattr(m, "settlement_time", "?"))

        sv_str = f"{sv}¢" if sv not in ("?", None) else "?"
        print(f"{str(ticker):<35} {str(status):>10} {sv_str:>12} {str(st):^22}")

if cursor:
    print(f"\nMore historical markets available (cursor: {cursor!r})")

print(f"\nTotal shown: {len(markets)}")
print("\nNote: settlement_value=100 means YES resolved, settlement_value=0 means NO resolved.")
