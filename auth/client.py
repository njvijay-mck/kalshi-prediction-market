"""Shared auth module — every script imports from here.

Usage:
    from auth.client import get_client           # KalshiClient (sync REST)
    from auth.client import get_ws_url           # WebSocket URL string
    from auth.client import build_ws_headers     # RSA-PSS signed WS headers
    from auth.client import raw_get              # Raw authenticated GET → dict
    from auth.client import raw_post             # Raw authenticated POST → dict
    from auth.client import raw_delete           # Raw authenticated DELETE → dict
"""

import base64
import datetime
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from kalshi_python_sync import Configuration, KalshiClient

load_dotenv()

DEMO_REST = "https://demo-api.kalshi.co/trade-api/v2"
PROD_REST = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_WS = "wss://demo-api.kalshi.co/trade-api/ws/v2"
PROD_WS = "wss://api.elections.kalshi.com/trade-api/ws/v2"


def _is_demo() -> bool:
    return os.getenv("KALSHI_ENV", "demo").lower() != "prod"


def _base_url() -> str:
    return DEMO_REST if _is_demo() else PROD_REST


def get_client() -> KalshiClient:
    """Return a KalshiClient pointed at demo or prod.

    If KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH are set, the client is
    authenticated and can call private endpoints. If credentials are missing,
    the client still works for public endpoints (markets, exchange status, etc.).

    KalshiClient proxies all API methods flat (get_markets, get_balance, etc.)
    by delegating to the appropriate sub-API internally.
    """
    config = Configuration(host=_base_url())
    key_id = os.getenv("KALSHI_API_KEY_ID")
    key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    if key_id and key_path:
        config.api_key_id = key_id
        config.private_key_pem = Path(key_path).read_text()
    return KalshiClient(configuration=config)


def get_ws_url() -> str:
    """Return the WebSocket base URL for the configured environment."""
    return DEMO_WS if _is_demo() else PROD_WS


def build_ws_headers() -> dict[str, str]:
    """Build RSA-PSS signed headers for the WebSocket handshake.

    The SDK doesn't expose a WebSocket client, so we sign manually.
    Signing formula: timestamp_ms + "GET" + "/trade-api/ws/v2"

    Re-call on every reconnect — stale timestamps are rejected by the server.
    """
    return _sign_headers("GET", "/trade-api/ws/v2")


def _sign_headers(method: str, path: str) -> dict[str, str]:
    """Build RSA-PSS signed auth headers for any request."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key_path = os.environ["KALSHI_PRIVATE_KEY_PATH"]
    private_key = serialization.load_pem_private_key(
        Path(key_path).read_bytes(), password=None
    )
    ts = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000))
    msg = (ts + method.upper() + path).encode()
    sig = private_key.sign(
        msg,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": os.environ["KALSHI_API_KEY_ID"],
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
        "Content-Type": "application/json",
    }


def raw_get(path: str, timeout: int = 30, _retries: int = 3, **params: Any) -> dict:
    """GET request that returns a raw dict (bypasses SDK pydantic validation).

    Uses auth headers when credentials are configured; otherwise makes a public request.
    Use this when the SDK model raises validation errors due to null fields in demo env.
    path: path relative to base URL, e.g. "/markets" or "/portfolio/balance"
    timeout: per-request read timeout in seconds (default 30)
    _retries: number of retry attempts on timeout/connection errors (default 3)
    """
    import time as _time

    import requests as req
    from requests.exceptions import ConnectionError as ReqConnectionError
    from requests.exceptions import Timeout

    url = _base_url() + path
    full_path = "/trade-api/v2" + path
    filtered = {k: v for k, v in params.items() if v is not None}

    # Use auth headers only if credentials are available
    if os.getenv("KALSHI_API_KEY_ID") and os.getenv("KALSHI_PRIVATE_KEY_PATH"):
        headers = _sign_headers("GET", full_path)
    else:
        headers = {"Content-Type": "application/json"}

    last_exc: Exception | None = None
    for attempt in range(_retries):
        try:
            r = req.get(url, headers=headers, params=filtered, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except (Timeout, ReqConnectionError) as exc:
            last_exc = exc
            if attempt < _retries - 1:
                _time.sleep(2 ** attempt)  # 1s, 2s, 4s backoff
                # Re-sign headers on retry (timestamp must be fresh)
                if os.getenv("KALSHI_API_KEY_ID") and os.getenv("KALSHI_PRIVATE_KEY_PATH"):
                    headers = _sign_headers("GET", full_path)
    raise last_exc  # type: ignore[misc]


def raw_post(path: str, body: dict) -> dict:
    """Authenticated POST that returns a raw dict."""
    import requests as req

    url = _base_url() + path
    full_path = "/trade-api/v2" + path
    headers = _sign_headers("POST", full_path)
    r = req.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json() if r.content else {}


def raw_delete(path: str, body: dict | None = None) -> dict:
    """Authenticated DELETE that returns a raw dict."""
    import requests as req

    url = _base_url() + path
    full_path = "/trade-api/v2" + path
    headers = _sign_headers("DELETE", full_path)
    r = req.delete(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json() if r.content else {}
