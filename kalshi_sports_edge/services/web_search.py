"""Enhanced Brave Search API wrapper with multi-source parallel search.

Searches multiple sources (Reddit, Yahoo Sports, ESPN, X, general web) in parallel
to gather comprehensive context for sports market analysis.
"""

from __future__ import annotations

import concurrent.futures
import os
from dataclasses import dataclass, field
from typing import Protocol

import httpx

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
MAX_SNIPPET_LEN = 400   # chars per result snippet
MAX_CONTEXT_PER_SOURCE = 800  # max chars per source


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = "general"  # reddit, yahoo, espn, x, general


@dataclass
class MultiSourceContext:
    """Aggregated context from multiple web sources."""
    reddit: list[SearchResult] = field(default_factory=list)
    yahoo: list[SearchResult] = field(default_factory=list)
    espn: list[SearchResult] = field(default_factory=list)
    x: list[SearchResult] = field(default_factory=list)
    general: list[SearchResult] = field(default_factory=list)
    
    def all_results(self) -> list[SearchResult]:
        """Return all results combined."""
        return self.reddit + self.yahoo + self.espn + self.x + self.general
    
    def build_context_string(self, anchor: str) -> str:
        """Format all search results into a structured markdown string."""
        lines = [f"## Web Research Context: {anchor}\n"]
        
        sections = [
            ("Reddit Discussions", self.reddit),
            ("Yahoo Sports", self.yahoo),
            ("ESPN News", self.espn),
            ("X/Twitter Sentiment", self.x),
            ("General Web", self.general),
        ]
        
        for section_name, results in sections:
            if results:
                lines.append(f"\n### {section_name}\n")
                for r in results[:3]:  # Top 3 per source
                    snippet = r.snippet[:MAX_SNIPPET_LEN].strip()
                    lines.append(f"- **{r.title}**: {snippet}")
        
        return "\n".join(lines)


class ProgressCallback(Protocol):
    """Protocol for progress reporting."""
    def __call__(self, message: str) -> None: ...


def search_game_context(
    game_title: str,
    team_a: str,
    team_b: str,
    sport: str | None = None,
    progress: ProgressCallback | None = None,
) -> MultiSourceContext:
    """Search multiple sources for comprehensive game context.
    
    Args:
        game_title: Full game title (e.g., "Boston at Phoenix")
        team_a: Team A name
        team_b: Team B name  
        sport: Sport type (basketball, soccer, etc.)
        progress: Optional callback for progress updates
    
    Returns:
        MultiSourceContext with aggregated results from all sources
    """
    if progress:
        progress(f"Searching web context for: {team_a} vs {team_b}...")
    
    # Build sport-specific search queries
    sport_terms = _get_sport_terms(sport)
    base_query = f"{team_a} vs {team_b}"
    
    # Define source-specific queries
    source_queries = {
        'reddit': [
            f"site:reddit.com/r/nba {base_query} {sport_terms}",
            f"site:reddit.com/r/sportsbook {base_query} pick",
        ],
        'yahoo': [
            f"site:sports.yahoo.com {base_query}",
            f"site:yahoo.com {base_query} odds prediction",
        ],
        'espn': [
            f"site:espn.com {base_query} preview",
            f"site:espn.com {team_a} {team_b} injury",
        ],
        'x': [
            f"site:twitter.com OR site:x.com {base_query} prediction",
            f"site:twitter.com OR site:x.com {team_a} {team_b} bet",
        ],
        'general': [
            f"{base_query} prediction odds {sport_terms}",
            f"{team_a} vs {team_b} injury report news",
        ],
    }
    
    context = MultiSourceContext()
    
    # Execute searches in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_source = {}
        
        for source, queries in source_queries.items():
            for query in queries:
                future = executor.submit(_brave_search_source, query, source, 3)
                future_to_source[future] = source
        
        completed = 0
        total = len(future_to_source)
        
        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            completed += 1
            
            if progress:
                progress(f"  [{completed}/{total}] Searching {source}...")
            
            try:
                results = future.result()
                if source == 'reddit':
                    context.reddit.extend(results)
                elif source == 'yahoo':
                    context.yahoo.extend(results)
                elif source == 'espn':
                    context.espn.extend(results)
                elif source == 'x':
                    context.x.extend(results)
                else:
                    context.general.extend(results)
            except Exception:
                pass  # Non-fatal: skip failed searches
    
    if progress:
        total_results = len(context.all_results())
        progress(f"  Found {total_results} context items from web sources")
    
    return context


def search_general(query: str, count: int = 5) -> list[SearchResult]:
    """General web search for market context (stats, news, analysis)."""
    return _brave_search_source(query, "general", count)


def search_social(query: str, count: int = 5) -> list[SearchResult]:
    """Recent-results search to approximate social/sentiment signal."""
    return _brave_search(query, count=count, freshness="pd", source="x")


def build_context_string(anchor: str, results: list[SearchResult]) -> str:
    """Format search results into a compact markdown string for LLM injection."""
    if not results:
        return ""
    lines = [f"## Web context for: {anchor}\n"]
    for r in results[:5]:
        snippet = r.snippet[:MAX_SNIPPET_LEN].strip()
        lines.append(f"**{r.title}**\n{snippet}\nSource: {r.url}\n")
    return "\n".join(lines)[:MAX_CONTEXT_PER_SOURCE * 2]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_sport_terms(sport: str | None) -> str:
    """Get sport-specific search terms."""
    if not sport:
        return ""
    sport_lower = sport.lower()
    terms = {
        'basketball': 'NBA NCAA',
        'soccer': 'football Premier League La Liga',
        'tennis': 'ATP WTA Grand Slam',
        'football': 'NFL NCAAF',
        'baseball': 'MLB',
        'hockey': 'NHL',
    }
    return terms.get(sport_lower, "")


def _brave_search_source(
    query: str, source: str, count: int = 5
) -> list[SearchResult]:
    """Execute Brave search and tag results with source."""
    results = _brave_search(query, count=count, freshness=None)
    for r in results:
        r.source = source
    return results


def _brave_search(
    query: str, count: int = 5, freshness: str | None = None, source: str = "general"
) -> list[SearchResult]:
    """Execute Brave search API call."""
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
                source=source,
            )
        )
    return results
