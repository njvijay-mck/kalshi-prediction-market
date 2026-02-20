"""02_market_discovery/04_get_event.py

Demonstrates: client.get_event(event_ticker=..., with_nested_markets=True)
- Fetches an event AND all its embedded markets in a single call.
- Public endpoint: no credentials needed.

SDK method: get_event(event_ticker: str, with_nested_markets: bool)
SDK response type: GetEventResponse
  .event  -> EventData (event_ticker, series_ticker, title, category, markets)
  .markets -> list[Market] (separate field when with_nested_markets=True)

Note: Lists events via raw_get() to avoid SDK pydantic validation errors on demo markets.
      Then uses the SDK get_event() call which handles the nested Event structure.

Run:
    uv run python 02_market_discovery/04_get_event.py
"""

from auth.client import get_client, raw_get

client = get_client()

# Find the first open event via raw HTTP (avoid SDK market validation issues)
data = raw_get("/events", status="open", limit=1)
events = data.get("events", [])
if not events:
    print("No open events found — cannot continue.")
    raise SystemExit(1)

event_ticker = events[0].get("event_ticker", events[0].get("ticker", "?"))
print(f"=== Event Detail (with nested markets): {event_ticker} ===\n")

# Get full event detail with embedded markets (raw to avoid validation issues)
event_data = raw_get(f"/events/{event_ticker}", with_nested_markets=True)
event = event_data.get("event", {})
markets = event_data.get("markets", event.get("markets", []))

# Print event-level fields
print("Event:")
for field in ("event_ticker", "series_ticker", "title", "category", "sub_title"):
    val = event.get(field)
    if val is not None:
        print(f"  {field:20s}: {val}")

# Print embedded markets
print(f"\nMarkets ({len(markets)} total):")
for m in markets[:5]:
    ticker = m.get("ticker", "?")
    title = m.get("title", m.get("subtitle", "?"))
    yes_bid = m.get("yes_bid")
    yes_ask = m.get("yes_ask")
    volume = m.get("volume")
    print(f"  {ticker}")
    print(f"    title   : {title}")
    print(f"    yes_bid : {yes_bid}¢  yes_ask: {yes_ask}¢")
    print(f"    volume  : {volume}")
    print()

if len(markets) > 5:
    print(f"  ... and {len(markets) - 5} more markets")

print("Note: with_nested_markets=True avoids N+1 calls to fetch each market.")
