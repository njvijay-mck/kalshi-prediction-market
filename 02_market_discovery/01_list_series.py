"""02_market_discovery/01_list_series.py

Demonstrates: GET /series  (series list — top of market hierarchy)
- Top level of the market hierarchy: Series → Events → Markets.
- Public endpoint: no credentials needed.

Note: Uses raw_get() instead of client.get_series_list() because the demo
      environment returns null for some required SDK model fields (e.g. tags).

Run:
    uv run python 02_market_discovery/01_list_series.py
"""

from auth.client import raw_get

MAX_SERIES = 10

print("=== Series List (top-level market hierarchy) ===\n")
data = raw_get("/series")
series_list = data.get("series", [])

if not series_list:
    print("No series returned.")
else:
    for s in series_list[:MAX_SERIES]:
        print(f"  ticker   : {s.get('ticker')}")
        print(f"  title    : {s.get('title')}")
        print(f"  category : {s.get('category')}")
        print(f"  frequency: {s.get('frequency')}")
        print(f"  tags     : {s.get('tags')}")
        print()

print(f"Showing up to {MAX_SERIES} of {len(series_list)} series.")
print("\nHierarchy: Series → Events → Markets")
print("A Series groups related Events (e.g., daily S&P 500 close levels).")
print("Each Event contains one or more Markets (binary yes/no contracts).")
