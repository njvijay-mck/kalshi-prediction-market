"""4-stage deep research pipeline for multi-market Kalshi sports analysis.

Stages (sequential — each feeds into the next):
  1. Research     — broad analysis of all markets + web context
  2. Critique     — challenge the research assumptions
  3. Rebuttal     — defend or revise estimates in light of critique
  4. Consolidation — final synthesis, position rankings, risk factors

Each stage prints a progress header before its LLM call (calls take 30-60s each).
The ConsolidatedReport preserves all four stage outputs for verbose display / PDF.
"""

from __future__ import annotations

import datetime

from kalshi_sports_edge.models import ConsolidatedReport, MarketData, OddsTable
from kalshi_sports_edge.services.llm_pipeline import (
    AnthropicClientWrapper,
    AuthenticationError,
    OpenAIClientWrapper,
)


def run_deep_research(
    markets: list[MarketData],
    odds_tables: list[OddsTable],
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
    web_context: str | None = None,
) -> ConsolidatedReport:
    """Run the 4-stage agent pipeline and return a ConsolidatedReport.

    Stages are strictly sequential: each stage's output is passed as
    context to the next. Total runtime is typically 2-5 minutes.
    """
    market_summary = _build_market_summary(markets, odds_tables)

    print("  [1/4] Research stage — gathering facts and base rates...", flush=True)
    research = _research_stage(market_summary, web_context, client, model)

    print("  [2/4] Critique stage — challenging assumptions...", flush=True)
    critique = _critique_stage(research, client, model)

    print("  [3/4] Rebuttal stage — defending and revising estimates...", flush=True)
    rebuttal = _rebuttal_stage(research, critique, client, model)

    print("  [4/4] Consolidation stage — synthesizing final recommendations...", flush=True)
    consolidation = _consolidation_stage(research, critique, rebuttal, client, model)

    return ConsolidatedReport(
        generated_at=datetime.datetime.now(),
        markets=markets,
        odds_tables=odds_tables,
        research_output=research,
        critique_output=critique,
        rebuttal_output=rebuttal,
        consolidation_output=consolidation,
    )


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------


def _research_stage(
    market_summary: str,
    web_context: str | None,
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
) -> str:
    ctx_block = f"\n\n## Web Context\n{web_context}" if web_context else ""
    return _call(
        system=(
            "You are an expert sports analyst and prediction market researcher. "
            "Provide thorough, data-driven analysis grounded in statistics and recent performance."
        ),
        user=f"""Research these US sports prediction markets thoroughly.

{market_summary}{ctx_block}

For each market provide:
1. Key facts about the matchup or event
2. Recent form, injuries, home/away advantage, weather if relevant
3. Historical head-to-head and base rates for similar situations
4. Your estimated probability for YES and NO outcomes, with reasoning
5. Confidence level: HIGH / MEDIUM / LOW and why""",
        client=client,
        model=model,
    )


def _critique_stage(
    research: str, client: OpenAIClientWrapper | AnthropicClientWrapper, model: str
) -> str:
    return _call(
        system=(
            "You are a rigorous devil's advocate analyst. "
            "Your job is to find weaknesses in sports market research — not to agree."
        ),
        user=f"""Critique the following sports market research. For each market identify:

1. Logical gaps or missing information that could change the estimate
2. Potential cognitive biases (recency bias, favorite-longshot bias, narrative bias)
3. The strongest counter-argument against each probability estimate
4. Any key factors that were overlooked or underweighted

## Research to Critique
{research}

Be specific. Quote specific claims from the research and explain why they may be wrong.""",
        client=client,
        model=model,
    )


def _rebuttal_stage(
    research: str, critique: str, client: OpenAIClientWrapper | AnthropicClientWrapper, model: str
) -> str:
    return _call(
        system=(
            "You are the original sports analyst responding to a critique of your research. "
            "Where the critique is valid, update your estimates. "
            "Where it is weak, defend your position."
        ),
        user=f"""Respond point-by-point to the critique below.

## Original Research
{research}

## Critique
{critique}

For each critique point:
- If valid: acknowledge it and provide revised probability estimates
- If weak: explain why your original estimate stands

End with REVISED PROBABILITY ESTIMATES for each market's YES and NO outcomes.""",
        client=client,
        model=model,
    )


def _consolidation_stage(
    research: str,
    critique: str,
    rebuttal: str,
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
) -> str:
    return _call(
        system=(
            "You are a senior sports betting portfolio manager. "
            "Synthesize multi-analyst input into clear, actionable position recommendations."
        ),
        user=f"""Synthesize the full research debate into a final report.

## Research
{research}

## Critique
{critique}

## Rebuttal
{rebuttal}

Produce your final report with these sections:

**FINAL PROBABILITY ESTIMATES**
For each market: YES prob / NO prob (after incorporating all debate).

**EDGE ANALYSIS**
Compare final probs vs market-implied prices. State edge for each side.
Edge = your_prob - market_implied_prob.

**POSITION RECOMMENDATIONS**
List only markets where |edge| > 5%. For each:
- RECOMMENDED: YES or NO
- Edge: X.X%
- EV: $X.XXX per $1 wagered
- Rationale: one sentence

**CONVICTION RANKING**
Rank all markets from highest to lowest conviction (confidence × edge magnitude).

**KEY RISKS**
Remaining uncertainties that could invalidate these recommendations.""",
        client=client,
        model=model,
        max_tokens=3000,
    )


# ---------------------------------------------------------------------------
# Shared LLM call
# ---------------------------------------------------------------------------


def _call(
    system: str,
    user: str,
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
    max_tokens: int = 2048,
) -> str:
    try:
        return client.chat(model=model, system=system, user=user, max_tokens=max_tokens)
    except Exception as exc:
        # Handle both OpenAI and Anthropic error types
        error_str = str(exc).lower()
        if "401" in str(exc) or "authentication" in error_str:
            raise AuthenticationError(
                "Authentication failed. Check your API key is valid for the selected provider."
            ) from exc
        if "403" in str(exc) or "permission" in error_str:
            raise AuthenticationError(
                "Kimi Code API access denied (403). The kimi.com/code API may be "
                "restricted to approved coding agents. Try --provider moonshot instead, "
                "or obtain a standard Moonshot API key from https://platform.moonshot.cn"
            ) from exc
        raise


# ---------------------------------------------------------------------------
# Market summary builder (shared input for research stage)
# ---------------------------------------------------------------------------


def _build_market_summary(markets: list[MarketData], tables: list[OddsTable]) -> str:
    lines = ["## Markets Under Analysis\n"]
    for m, t in zip(markets, tables):
        yes = t.yes_row
        no = t.no_row
        lines.append(
            f"**{m.title}** ({m.ticker})\n"
            f"  YES: {yes.price_cents}¢  implied {yes.implied_prob:.1%}  {yes.american_odds:+d}\n"
            f"  NO:  {no.price_cents}¢  implied {no.implied_prob:.1%}  {no.american_odds:+d}\n"
            f"  Volume: {m.volume:,} contracts  |  OI: {m.open_interest:,}\n"
            f"  Close: {m.close_time or 'N/A'}\n"
        )
    return "\n".join(lines)
