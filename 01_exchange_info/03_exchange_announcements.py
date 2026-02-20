"""01_exchange_info/03_exchange_announcements.py

Demonstrates: client.get_exchange_announcements()
- Lists exchange announcements.
- Note: this endpoint returns all at once (no cursor pagination in current SDK).
- Public endpoint: no credentials needed.

SDK response type: GetExchangeAnnouncementsResponse
  .announcements -> list[Announcement]
    Announcement fields: type, message, delivery_time, status

Run:
    uv run python 01_exchange_info/03_exchange_announcements.py
"""

from auth.client import get_client

client = get_client()

print("=== Exchange Announcements ===\n")
resp = client.get_exchange_announcements()
announcements = resp.announcements or []

if not announcements:
    print("No announcements returned.")
else:
    for i, ann in enumerate(announcements, 1):
        print(f"[{i}]")
        print(f"  type         : {ann.type}")
        print(f"  status       : {ann.status}")
        print(f"  delivery_time: {ann.delivery_time}")
        print(f"  message      : {ann.message}")
        print()

print(f"Total: {len(announcements)} announcement(s)")
print("\nNote: Other list endpoints (markets, events, orders) use cursor pagination.")
print("  Pattern: pass cursor=resp.cursor until resp.cursor is None/empty.")
