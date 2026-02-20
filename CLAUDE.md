# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python application for interacting with the Kalshi prediction market platform. Contains ~32 self-contained demo scripts covering the full Kalshi REST + WebSocket API surface.

## SDKs

- `kalshi_python_sync` — synchronous REST client (all scripts in 01–09 folders)
- `kalshi_python_async` — async client (WebSocket scripts in 10_websocket/)
- Old `kalshi-python` package is **deprecated** — do not use it

## Auth Module

`auth/client.py` — import from every script:

```python
from auth.client import get_client          # KalshiClient (sync REST)
from auth.client import get_ws_url          # WebSocket URL
from auth.client import build_ws_headers    # RSA-PSS signed WS auth headers
```

- `KALSHI_ENV=demo` in `.env` → points to `demo-api.kalshi.co`
- `KALSHI_ENV=prod`  → points to `api.elections.kalshi.com`

## Expected Toolchain

- **Package manager:** `uv` (preferred)
- **Linter/formatter:** `ruff`
- **Type checker:** `mypy`
- **Test runner:** `pytest`

## Common Commands

```bash
uv sync                                          # Install dependencies
uv run python 01_exchange_info/01_exchange_status.py  # Run any script
uv run pytest                                    # Run all tests
uv run ruff check .                              # Lint
uv run ruff format .                             # Format
uv run mypy .                                    # Type check
```

## Environment

Copy `.env.example` to `.env` and fill in:
- `KALSHI_API_KEY_ID` — from demo.kalshi.co API settings
- `KALSHI_PRIVATE_KEY_PATH` — path to RSA private key PEM file
- `KALSHI_ENV=demo` — use demo environment by default

## API Docs

Local reference: `docs/kalshi_api_reference.md`
