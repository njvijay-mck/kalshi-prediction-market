"""09_account_management/01_get_api_keys.py

Demonstrates: client.get_api_keys()
- Lists your API keys with metadata.
- Read-only — does not create or delete keys.
- Requires credentials in .env

SDK method: get_api_keys()
SDK response type: GetApiKeysResponse
  .api_keys -> list[ApiKey]
    ApiKey fields: api_key_id, name, scopes

Run:
    uv run python 09_account_management/01_get_api_keys.py
"""

from auth.client import get_client

client = get_client()

print("=== API Keys ===\n")
resp = client.get_api_keys()
api_keys = resp.api_keys or []

if not api_keys:
    print("No API keys returned.")
    print("Manage keys at: https://demo.kalshi.co (Settings → API)")
else:
    for key in api_keys:
        print(f"  api_key_id : {key.api_key_id}")
        print(f"  name       : {key.name}")
        print(f"  scopes     : {key.scopes}")
        print()

print(f"Total keys: {len(api_keys)}")
print("\nNote: Keep your private key PEM file secure — it cannot be recovered if lost.")
