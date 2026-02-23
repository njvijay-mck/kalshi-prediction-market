"""Enhanced deep research pipeline with multi-source web search and comprehensive metrics.

Stages:
  1. Web Research     — Multi-source parallel search (Reddit, Yahoo, ESPN, X)
  2. Probability Est  — LLM estimates true probabilities with web context
  3. Edge/EV/ROI Calc — Calculate all metrics
  4. Classification   — Sentiment, confidence, and reason tagging
  5. Consolidation    — Final synthesis with rankings
"""

from __future__ import annotations

import concurrent.futures
import datetime
from typing import Protocol

from kalshi_sports_edge.models import (
    ConsolidatedReport,
    MarketAnalysis,
    MarketData,
    OddsTable,
)
from kalshi_sports_edge.services.llm_pipeline import (
    AnthropicClientWrapper,
    AuthenticationError,
    OpenAIClientWrapper,
)
from kalshi_sports_edge.services.web_search import (
    MultiSourceContext,
    search_game_context,
)


class ProgressCallback(Protocol):
    """Protocol for progress reporting."""
    def __call__(self, message: str) -> None: ...


def run_deep_research(
    markets: list[MarketData],
    odds_tables: list[OddsTable],
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
    web_context: str | None = None,
    progress: ProgressCallback | None = None,
) -> ConsolidatedReport:
    """Run the enhanced deep research pipeline with multi-source web search.
    
    Args:
        markets: List of markets to analyze
        odds_tables: Corresponding odds tables
        client: LLM client
        model: Model name to use
        web_context: Optional pre-fetched web context (legacy)
        progress: Optional progress callback
    
    Returns:
        ConsolidatedReport with enhanced analysis
    """
    if progress:
        progress(f"Starting deep research on {len(markets)} markets...")
    
    # Stage 1: Multi-source web research for each game
    if progress:
        progress("\n[1/5] Web Research — gathering data from Reddit, Yahoo, ESPN, X...")
    
    game_contexts = _fetch_all_game_contexts(markets, progress)
    
    # Stage 2-3: Parallel probability estimation and metrics calculation
    if progress:
        progress("\n[2/5] Probability Estimation — LLM analysis with web context...")
    
    analyses = _analyze_all_markets(
        markets, odds_tables, game_contexts, client, model, progress
    )
    
    # Stage 4: Classification (sentiment, confidence)
    if progress:
        progress("\n[3/5] Classification — calculating sentiment and confidence...")
    
    analyses = _classify_all_markets(analyses)
    
    # Stage 5: Consolidation
    if progress:
        progress("\n[4/5] Consolidation — generating rankings and recommendations...")
    
    consolidation = _build_consolidation_output(analyses)
    
    if progress:
        progress("\n[5/5] Complete!")
    
    report = ConsolidatedReport(
        generated_at=datetime.datetime.now(),
        markets=markets,
        odds_tables=odds_tables,
        research_output=_build_research_summary(analyses),
        critique_output="",  # Integrated into probability estimation
        rebuttal_output="",  # Integrated into probability estimation
        consolidation_output=consolidation,
    )
    
    # Store analyses for enhanced output (attached dynamically)
    report._analyses = analyses
    
    return report


def _fetch_all_game_contexts(
    markets: list[MarketData],
    progress: ProgressCallback | None = None,
) -> dict[str, MultiSourceContext]:
    """Fetch web context for all unique games."""
    # Group markets by event_ticker to avoid duplicate searches
    event_to_markets: dict[str, MarketData] = {}
    for m in markets:
        if m.event_ticker not in event_to_markets:
            event_to_markets[m.event_ticker] = m
    
    contexts: dict[str, MultiSourceContext] = {}
    total = len(event_to_markets)
    
    for i, (event_ticker, market) in enumerate(event_to_markets.items(), 1):
        if progress:
            progress(f"  [{i}/{total}] Researching {market.yes_team or 'Team A'} vs {market.no_team or 'Team B'}...")
        
        context = search_game_context(
            game_title=market.title,
            team_a=market.yes_team or "Team A",
            team_b=market.no_team or "Team B",
            progress=lambda msg: progress(f"    {msg}") if progress else None,
        )
        contexts[event_ticker] = context
    
    return contexts


def _analyze_all_markets(
    markets: list[MarketData],
    odds_tables: list[OddsTable],
    game_contexts: dict[str, MultiSourceContext],
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
    progress: ProgressCallback | None = None,
) -> list[MarketAnalysis]:
    """Analyze all markets with LLM to get true probability estimates."""
    analyses: list[MarketAnalysis] = []
    total = len(markets)
    
    for i, (market, odds_table) in enumerate(zip(markets, odds_tables), 1):
        if progress:
            progress(f"  [{i}/{total}] Analyzing {market.ticker}...")
        
        # Get context for this market's game
        context = game_contexts.get(market.event_ticker, MultiSourceContext())
        context_str = context.build_context_string(market.title)
        
        # LLM probability estimation
        llm_yes_prob, llm_no_prob, analysis_text, confidence, reason = _estimate_probabilities(
            market, odds_table, context_str, client, model
        )
        
        # Calculate metrics
        market_yes = odds_table.yes_row.implied_prob
        market_no = odds_table.no_row.implied_prob
        
        yes_edge = llm_yes_prob - market_yes
        no_edge = llm_no_prob - market_no
        
        yes_price = odds_table.yes_row.price_cents / 100.0
        no_price = odds_table.no_row.price_cents / 100.0
        
        yes_ev = yes_edge
        no_ev = no_edge
        
        yes_roi = (yes_ev / yes_price * 100) if yes_price > 0 else 0
        no_roi = (no_ev / no_price * 100) if no_price > 0 else 0
        
        # Determine best side
        if yes_edge >= no_edge:
            best_edge = yes_edge
            best_ev = yes_ev
            best_side = "YES"
            best_roi = yes_roi
        else:
            best_edge = no_edge
            best_ev = no_ev
            best_side = "NO"
            best_roi = no_roi
        
        analysis = MarketAnalysis(
            market=market,
            odds_table=odds_table,
            llm_yes_prob=llm_yes_prob,
            llm_no_prob=llm_no_prob,
            yes_edge=yes_edge,
            no_edge=no_edge,
            yes_ev=yes_ev,
            no_ev=no_ev,
            yes_roi=yes_roi,
            no_roi=no_roi,
            best_edge=best_edge,
            best_ev=best_ev,
            best_side=best_side,
            best_roi=best_roi,
            sentiment="Neutral",  # Will be updated in classification stage
            confidence=confidence,
            reason=reason,
            web_context=context_str,
            llm_analysis=analysis_text,
        )
        
        analyses.append(analysis)
    
    return analyses


def _estimate_probabilities(
    market: MarketData,
    odds_table: OddsTable,
    web_context: str,
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
) -> tuple[float, float, str, str, str]:
    """Use LLM to estimate true probabilities with web context."""
    yes = odds_table.yes_row
    no = odds_table.no_row
    
    prompt = f"""Analyze this sports prediction market using the provided web research context.

**Market:** {market.title}
**Ticker:** {market.ticker}

**Current Market Prices:**
- YES ({market.yes_team or 'Team A'}): {yes.price_cents}¢ (implied {yes.implied_prob:.1%})
- NO ({market.no_team or 'Team B'}): {no.price_cents}¢ (implied {no.implied_prob:.1%})

**Volume:** {market.volume:,} contracts | **OI:** {market.open_interest:,} contracts

{web_context}

Based on the web research above, plus your knowledge of this sport:

1. What is the TRUE probability of YES winning? (0-100%)
2. What is the TRUE probability of NO winning? (0-100%)
3. What is your confidence level? (High/Medium/Low)
4. What is the PRIMARY reason for your estimate? (stats/injury/form/news/data/record/consensus/volume/schedule/weather/momentum/unclear)

Respond in this exact format:

<analysis>
Brief analysis (2-3 sentences) covering key factors: recent form, injuries, matchups, public sentiment, etc.
</analysis>

<probabilities>
YES: XX.X%
NO: XX.X%
</probabilities>

<confidence>
Level: High/Medium/Low
Reason: stats/injury/form/news/data/record/consensus/volume/schedule/weather/momentum/unclear
</confidence>"""

    try:
        response = client.chat(
            model=model,
            system="You are an expert sports analyst. Use web research context to estimate true probabilities. Be objective and data-driven.",
            user=prompt,
            max_tokens=800,
        )
        
        # Parse response
        yes_prob = _extract_probability(response, "YES")
        no_prob = _extract_probability(response, "NO")
        
        # Normalize if they don't sum to 1
        total = yes_prob + no_prob
        if total > 0 and abs(total - 1.0) > 0.01:
            yes_prob = yes_prob / total
            no_prob = no_prob / total
        
        analysis_text = _extract_tag(response, "analysis") or "No analysis provided."
        confidence = _extract_confidence(response)
        reason = _extract_reason(response)
        
        return yes_prob, no_prob, analysis_text, confidence, reason
        
    except Exception:
        # Fallback: use market implied probabilities
        return yes.implied_prob, no.implied_prob, "Analysis failed.", "Low", "unclear"


def _classify_all_markets(analyses: list[MarketAnalysis]) -> list[MarketAnalysis]:
    """Classify sentiment and adjust confidence based on metrics."""
    for analysis in analyses:
        # Sentiment based on best edge
        if analysis.best_edge >= 0.05:
            analysis.sentiment = "Bullish"
        elif analysis.best_edge <= -0.05:
            analysis.sentiment = "Bearish"
        else:
            analysis.sentiment = "Neutral"
        
        # Adjust confidence based on volume/liquidity
        if analysis.market.volume > 10000 and analysis.confidence == "High":
            analysis.confidence = "High"  # Keep high if high volume
        elif analysis.market.volume < 1000 and analysis.confidence == "High":
            analysis.confidence = "Medium"  # Downgrade if low volume
        elif analysis.market.volume < 500:
            analysis.confidence = "Low"  # Low volume = low confidence
    
    return analyses


def _build_consolidation_output(analyses: list[MarketAnalysis]) -> str:
    """Build the final consolidation output with rankings."""
    lines = []
    
    # Header
    lines.append("=" * 70)
    lines.append("CONSOLIDATED DEEP RESEARCH REPORT")
    lines.append("=" * 70)
    lines.append("")
    
    # Top Picks by Edge (|edge| >= 5%)
    lines.append("TOP PICKS BY EDGE (|Edge| >= 5%)")
    lines.append("-" * 70)
    
    edge_sorted = sorted(
        [a for a in analyses if abs(a.best_edge) >= 0.05],
        key=lambda x: abs(x.best_edge),
        reverse=True
    )
    
    for i, analysis in enumerate(edge_sorted[:15], 1):
        side = analysis.best_side
        edge_pct = analysis.best_edge * 100
        ev_c = analysis.best_ev
        rec = "BUY" if analysis.best_edge >= 0.05 else "SELL"
        lines.append(
            f"#{i:2d} {analysis.market.title[:45]:45s} | "
            f"Edge: {edge_pct:+5.1f}% | EV: {ev_c:+.3f}/c | {rec}"
        )
    
    lines.append("")
    
    # Top Picks by EV (positive EV only)
    lines.append("TOP PICKS BY EV (Positive EV Only)")
    lines.append("-" * 70)
    
    ev_sorted = sorted(
        [a for a in analyses if a.best_ev > 0],
        key=lambda x: x.best_ev,
        reverse=True
    )
    
    for i, analysis in enumerate(ev_sorted[:15], 1):
        roi_pct = analysis.best_roi
        lines.append(
            f"#{i:2d} {analysis.market.title[:45]:45s} | "
            f"EV: {analysis.best_ev:+.3f}/c | ROI: {roi_pct:+6.1f}%"
        )
    
    lines.append("")
    
    # Markets to Avoid
    lines.append("MARKETS TO AVOID (No Edge or Negative EV)")
    lines.append("-" * 70)
    
    avoid_list = [a for a in analyses if abs(a.best_edge) < 0.05 or a.best_ev <= 0]
    for analysis in avoid_list[:10]:
        lines.append(
            f"   {analysis.market.title[:50]:50s} | "
            f"Edge: {analysis.best_edge*100:+.1f}% | EV: {analysis.best_ev:+.3f}/c"
        )
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def _build_research_summary(analyses: list[MarketAnalysis]) -> str:
    """Build a summary of all research findings."""
    lines = ["Market Analysis Summary\n"]
    
    for analysis in analyses:
        lines.append(f"\n{analysis.market.title}")
        lines.append(f"  Market YES: {analysis.market_yes_implied:.1%} → LLM: {analysis.llm_yes_prob:.1%}")
        lines.append(f"  Market NO:  {analysis.market_no_implied:.1%} → LLM: {analysis.llm_no_prob:.1%}")
        lines.append(f"  Best Edge: {analysis.best_edge:+.1%} ({analysis.best_side})")
        lines.append(f"  Confidence: {analysis.confidence} | Reason: {analysis.reason}")
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------


def _extract_probability(text: str, side: str) -> float:
    """Extract probability for a side from LLM response."""
    import re
    
    # Look for patterns like "YES: 65.5%" or "YES probability: 65.5%"
    patterns = [
        rf"{side}:\s*(\d+\.?\d*)%",
        rf"{side}\s*probability:\s*(\d+\.?\d*)%",
        rf"{side}\s*=\s*(\d+\.?\d*)%",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 100.0
    
    return 0.5  # Default fallback


def _extract_tag(text: str, tag: str) -> str | None:
    """Extract content between XML-style tags."""
    import re
    
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_confidence(text: str) -> str:
    """Extract confidence level from LLM response."""
    import re
    
    match = re.search(r"Level:\s*(High|Medium|Low)", text, re.IGNORECASE)
    if match:
        return match.group(1).capitalize()
    return "Medium"


def _extract_reason(text: str) -> str:
    """Extract reason tag from LLM response."""
    import re
    
    valid_reasons = ["stats", "injury", "form", "news", "data", "record", 
                     "consensus", "volume", "schedule", "weather", "momentum", "unclear"]
    
    match = re.search(r"Reason:\s*(\w+)", text, re.IGNORECASE)
    if match:
        reason = match.group(1).lower()
        if reason in valid_reasons:
            return reason
    
    return "data"


# Legacy function for backward compatibility
def _call(
    system: str,
    user: str,
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
    max_tokens: int = 2048,
) -> str:
    """Make LLM call with error handling."""
    try:
        return client.chat(model=model, system=system, user=user, max_tokens=max_tokens)
    except Exception as exc:
        error_str = str(exc).lower()
        if "401" in str(exc) or "authentication" in error_str:
            raise AuthenticationError("Authentication failed. Check your API key.") from exc
        raise
