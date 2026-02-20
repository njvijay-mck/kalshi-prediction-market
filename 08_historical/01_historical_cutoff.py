"""08_historical/01_historical_cutoff.py

Demonstrates: GET /historical/cutoff
- Returns the timestamp boundary between "live" data (available in /markets, /trades, etc.)
  and "historical" data (only available under /historical/* endpoints).
- Markets/trades before the cutoff timestamp must be fetched from historical endpoints.
- Requires credentials in .env

Note: This endpoint may not be in the SDK yet — falls back to raw_get() direct HTTP.

Run:
    uv run python 08_historical/01_historical_cutoff.py
"""

import datetime

from auth.client import get_client, raw_get

client = get_client()

print("=== Historical Data Cutoff ===\n")

# Try SDK method first, fall back to raw HTTP
cutoff_ts = None
try:
    resp = client.get_historical_cutoff()  # type: ignore[attr-defined]
    cutoff_ts = getattr(resp, "cutoff_time", getattr(resp, "cutoff_timestamp", None))
    print("(Used SDK method)")
except AttributeError:
    data = raw_get("/historical/cutoff")
    cutoff_ts = data.get("cutoff_time", data.get("cutoff_timestamp"))
    print("(Used raw HTTP — SDK method not available)")

if cutoff_ts is not None:
    print(f"\n  raw cutoff timestamp : {cutoff_ts}")
    if isinstance(cutoff_ts, (int, float)):
        dt = datetime.datetime.fromtimestamp(cutoff_ts, tz=datetime.timezone.utc)
        print(f"  cutoff datetime (UTC): {dt.isoformat()}")
    print("\nData before this cutoff must be fetched from /historical/* endpoints.")
    print("Data after this cutoff is available in the standard /markets, /trades, etc.")
else:
    print("Could not determine cutoff timestamp.")
