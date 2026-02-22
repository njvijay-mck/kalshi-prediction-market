"""Brave Search API wrapper for web context enrichment.

Non-fatal: if BRAVE_SEARCH_API_KEY is absent or the API call fails,
functions return empty lists and build_context_string returns "".
This allows the app to run without web search configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
MAX_SNIPPET_LEN = 300   # chars per result snippet
MAX_CONTEXT_LEN = 2000  # total context string length fed to LLM


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def search_general(query: str, count: int = 5) -> list[SearchResult]:
    """General web search for market context (stats, news, analysis)."""
    return _brave_search(query, count=count, freshness=None)


def search_social(query: str, count: int = 5) -> list[SearchResult]:
    """Recent-results search to approximate social/sentiment signal.

    Uses Brave's freshness="pd" (past day) to surface the most recent content.
    """
    return _brave_search(query, count=count, freshness="pd")


def build_context_string(anchor: str, results: list[SearchResult]) -> str:
    """Format search results into a compact markdown string for LLM injection.

    Each snippet is truncated to MAX_SNIPPET_LEN. Total output capped at MAX_CONTEXT_LEN.
    Returns "" if results is empty.
    """
    if not results:
        return ""
    lines = [f"## Web context for: {anchor}\n"]
    for r in results:
        snippet = r.snippet[:MAX_SNIPPET_LEN].strip()
        lines.append(f"**{r.title}**\n{snippet}\nSource: {r.url}\n")
    return "\n".join(lines)[:MAX_CONTEXT_LEN]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _brave_search(
    query: str, count: int = 5, freshness: str | None = None
) -> list[SearchResult]:
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return []

    params: dict[str, object] = {"q": query, "count": count}
    if freshness:
        params["freshness"] = freshness

    try:
        resp = httpx.get(
            BRAVE_SEARCH_URL,
            headers={
                "X-Subscription-Token": api_key,
                "Accept": "application/json",
            },
            params=params,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results: list[SearchResult] = []
    for item in data.get("web", {}).get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
            )
        )
    return results
