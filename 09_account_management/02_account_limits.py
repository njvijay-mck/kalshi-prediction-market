"""09_account_management/02_account_limits.py

Demonstrates: GET /account/limits
- Rate limits, API tier, max open orders, max connections.
- Requires credentials in .env

Rate limit tiers:
  Basic    : 20 reads / 10s,  10 writes / 10s
  Advanced : 30 reads / 10s,  30 writes / 10s
  Premier  : 100 reads / 10s, 100 writes / 10s
  Prime    : 400 reads / 10s, 400 writes / 10s

Run:
    uv run python 09_account_management/02_account_limits.py
"""

from auth.client import get_client, raw_get

client = get_client()

print("=== Account Limits & Rate Limits ===\n")

# Try SDK method first, fall back to raw HTTP
limits_data: dict = {}
try:
    resp = client.get_account_limits()  # type: ignore[attr-defined]
    for attr in dir(resp):
        if not attr.startswith("_"):
            val = getattr(resp, attr, None)
            if not callable(val):
                limits_data[attr] = val
    print("(Used SDK method)\n")
except AttributeError:
    limits_data = raw_get("/account/limits")
    print("(Used raw HTTP — SDK method not available)\n")

if limits_data:
    for key, val in limits_data.items():
        print(f"  {key:40s}: {val}")
else:
    print("No limits data returned.")

print("\n--- Rate Limit Tier Reference ---")
print(f"  {'Tier':<12} {'Reads/10s':>10} {'Writes/10s':>12}")
print("  " + "-" * 36)
for tier, reads, writes in [
    ("Basic", 20, 10),
    ("Advanced", 30, 30),
    ("Premier", 100, 100),
    ("Prime", 400, 400),
]:
    print(f"  {tier:<12} {reads:>10} {writes:>12}")

print("\nBatch cancel cost: 0.2 write units per order (vs 1.0 for single cancel)")
print("Batch create cost: 1.0 write unit per batch call (regardless of order count)")
