"""04_portfolio/01_get_balance.py

Demonstrates: client.get_balance()
- First authenticated API call.
- Balance is stored as integer cents; divide by 100 for dollars.
- Requires: KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH in .env

SDK method: get_balance()
SDK response type: GetBalanceResponse
  .balance        -> int (cents)
  .portfolio_value -> int (cents)
  .updated_ts     -> int (unix timestamp)

Run:
    uv run python 04_portfolio/01_get_balance.py
"""

from auth.client import get_client

client = get_client()

print("=== Account Balance ===\n")
resp = client.get_balance()

print(f"  balance (cents)       : {resp.balance}")
print(f"  balance (dollars)     : ${resp.balance / 100:.2f}")
print(f"  portfolio_value (cents): {resp.portfolio_value}")
if resp.portfolio_value:
    print(f"  portfolio_value ($)   : ${resp.portfolio_value / 100:.2f}")
print(f"  updated_ts            : {resp.updated_ts}")

print("\nNote: This is your demo account balance — safe to use without real money risk.")
print("      balance is in cents. Divide by 100 to get dollars.")
