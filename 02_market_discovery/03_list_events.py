"""02_market_discovery/03_list_events.py

Demonstrates: GET /events?status=open with cursor pagination
- List open events with cursor pagination.
- Public endpoint: no credentials needed.

SDK method: get_events(status, limit, cursor, with_nested_markets)
Note: Using raw_get() to avoid SDK pydantic validation issues on demo market data.

Run:
    uv run python 02_market_discovery/03_list_events.py
"""

from auth.client import raw_get

MAX_EVENTS = 10
PAGE_LIMIT = 5

print("=== Open Events (cursor pagination demo) ===\n")

cursor = None
total = 0
page = 0

while total < MAX_EVENTS:
    page += 1
    params = {"status": "open", "limit": PAGE_LIMIT}
    if cursor:
        params["cursor"] = cursor

    data = raw_get("/events", **params)
    events = data.get("events", [])
    cursor = data.get("cursor")

    if not events:
        break

    for event in events:
        if total >= MAX_EVENTS:
            break
        total += 1
        event_ticker = event.get("event_ticker", event.get("ticker", "?"))
        title = event.get("title", "?")
        category = event.get("category", "?")
        markets = event.get("markets", [])
        print(f"  {event_ticker}")
        print(f"    title    : {title}")
        print(f"    category : {category}")
        print(f"    markets  : {len(markets)} embedded")
        print()

    print(f"  -- Page {page} done, cursor={cursor!r} --\n")

    if not cursor:
        print("No more pages.")
        break

print(f"Total events shown: {total}")
print("\nCursor pagination pattern:")
print("  cursor = None")
print("  while True:")
print("      data = raw_get('/events', status='open', limit=5, cursor=cursor)")
print("      for e in data['events']: process(e)")
print("      cursor = data.get('cursor')")
print("      if not cursor: break")
