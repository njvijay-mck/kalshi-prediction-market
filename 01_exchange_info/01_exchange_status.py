"""01_exchange_info/01_exchange_status.py

Demonstrates: client.get_exchange_status()
- First smoke test — confirms the API is reachable.
- Public endpoint: no credentials needed.

SDK response type: ExchangeStatus
  Fields: exchange_active, trading_active, exchange_estimated_resume_time

Run:
    uv run python 01_exchange_info/01_exchange_status.py
"""

from auth.client import get_client

client = get_client()

print("=== Exchange Status ===")
status = client.get_exchange_status()

print(f"exchange_active              : {status.exchange_active}")
print(f"trading_active               : {status.trading_active}")
print(f"exchange_estimated_resume_time: {status.exchange_estimated_resume_time}")
