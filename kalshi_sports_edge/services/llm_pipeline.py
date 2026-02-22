"""LLM single-pass analysis for Kalshi sports markets.

Both Claude and Kimi are accessed via OpenAI-compatible endpoints using the
openai Python SDK. Only the base_url, api_key, and model differ between providers.

Single-pass pipeline:
  1. Build a structured prompt with market data, odds table, and optional web context
  2. Make one LLM call
  3. Parse XML-tagged sections from the response into ReportData
"""

from __future__ import annotations

import os
import re

import openai

from kalshi_sports_edge.config import PROVIDER_BASE_URLS, PROVIDER_DEFAULT_MODELS, PROVIDER_ENV_KEYS
from kalshi_sports_edge.models import MarketData, OddsTable, ReportData


def get_llm_client(provider: str) -> openai.OpenAI:
    """Build an OpenAI-compatible client for the given provider.

    Both 'claude' and 'kimi' use the openai SDK with different base_url/api_key.
    Raises ValueError if the required API key env var is not set.
    """
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.environ.get(env_key)
    if not api_key:
        raise ValueError(
            f"Missing env var '{env_key}' required for provider '{provider}'. "
            f"Add it to your .env file."
        )
    return openai.OpenAI(
        api_key=api_key,
        base_url=PROVIDER_BASE_URLS[provider],
    )


def get_default_model(provider: str) -> str:
    return PROVIDER_DEFAULT_MODELS.get(provider, "claude-opus-4-6")


def run_single_pass(
    market: MarketData,
    odds_table: OddsTable,
    client: openai.OpenAI,
    model: str,
    web_context: str | None = None,
    edge_threshold: float = 0.05,
) -> ReportData:
    """Run one LLM call and return a populated ReportData.

    The prompt uses XML tags to structure the response into parseable sections.
    Parsing is tolerant — missing sections result in None fields, not errors.
    """
    prompt = _build_prompt(market, odds_table, web_context, edge_threshold)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1200,
    )
    raw = response.choices[0].message.content or ""
    return _parse_response(raw, market, odds_table, edge_threshold, web_context)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a sharp sports prediction market analyst specializing in US professional sports. "
    "You analyze Kalshi binary prediction markets and identify pricing inefficiencies. "
    "Ground your analysis in statistics, recent form, injuries, and historical base rates. "
    "Be concise and direct. Structure your output using the XML tags specified in each prompt."
)


def _build_prompt(
    market: MarketData,
    odds_table: OddsTable,
    web_context: str | None,
    edge_threshold: float,
) -> str:
    yes = odds_table.yes_row
    no = odds_table.no_row
    spread_note = (
        f"  ⚠ Wide bid/ask spread ({market.spread_cents}¢) — price may be imprecise."
        if odds_table.wide_spread
        else ""
    )
    ctx_block = f"\n\n## Web Context\n{web_context}" if web_context else ""

    # Build table rows as variables to keep line length within limits
    yes_row = (
        f"| YES | {yes.price_cents}¢ | {yes.implied_prob:.1%}"
        f" | {yes.decimal_odds:.3f} | {yes.american_odds:+d} | {yes.fractional_str} |"
    )
    no_row = (
        f"| NO  | {no.price_cents}¢ | {no.implied_prob:.1%}"
        f" | {no.decimal_odds:.3f} | {no.american_odds:+d} | {no.fractional_str} |"
    )

    return f"""Analyze this Kalshi US sports prediction market:

**Market:** {market.title}
**Ticker:** {market.ticker}
**Volume:** {market.volume:,} contracts  |  **Open Interest:** {market.open_interest:,} contracts
**Close:** {market.close_time or "N/A"}{spread_note}

**Odds Table (price source: {odds_table.price_source}):**
| Outcome | Price | Implied % | Decimal | American | Fractional |
|---------|-------|-----------|---------|----------|------------|
{yes_row}
{no_row}

Overround: {odds_table.overround:+.4f}{ctx_block}

Respond using ONLY these XML tags in order:

<summary>
One paragraph: what is this event, when does it resolve, which teams/players are involved?
</summary>

<analysis>
Assess the current pricing. Who is the market's implied favorite? Is the probability reasonable
given current form, injuries, home/away advantage, and historical matchup data?
Reference specific statistics or context where available.
</analysis>

<edge>
State your estimated true probability for YES and NO.
Calculate edge for each side (your_prob - market_implied):
YES: true_prob=[X.XX] implied={yes.implied_prob:.3f} edge=[±X.XXX]
NO:  true_prob=[X.XX] implied={no.implied_prob:.3f} edge=[±X.XXX]
Edge threshold: {edge_threshold:.1%}
</edge>

<recommend>
If the absolute edge for either side >= {edge_threshold:.1%}, write exactly:
RECOMMENDED POSITION: [YES or NO] — Edge: [X.X%] — EV: $[X.XXX] per $1 wagered
Otherwise write exactly:
PASS — edge below {edge_threshold:.1%} threshold
</recommend>"""


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_response(
    raw: str,
    market: MarketData,
    odds_table: OddsTable,
    edge_threshold: float,
    web_context: str | None,
) -> ReportData:
    def extract(tag: str) -> str | None:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", raw, re.DOTALL)
        return m.group(1).strip() if m else None

    recommend_text = extract("recommend") or ""
    recommended_side: str | None = None
    recommended_edge: float | None = None

    rec_match = re.search(
        r"RECOMMENDED POSITION:\s*(YES|NO).*?Edge:\s*([\d.]+)%",
        recommend_text,
        re.IGNORECASE,
    )
    if rec_match:
        recommended_side = rec_match.group(1).upper()
        recommended_edge = float(rec_match.group(2)) / 100.0

    sections = [extract(t) for t in ("summary", "analysis", "edge", "recommend")]
    llm_analysis = "\n\n".join(s for s in sections if s)

    return ReportData(
        market=market,
        odds_table=odds_table,
        llm_analysis=llm_analysis or None,
        recommended_side=recommended_side,
        recommended_edge=recommended_edge,
        web_context=web_context,
        edge_threshold_used=edge_threshold,
    )
