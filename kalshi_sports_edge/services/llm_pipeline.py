"""LLM single-pass analysis for Kalshi sports markets.

Providers:
  - claude: Uses Anthropic SDK (api.anthropic.com)
  - kimi: Uses Anthropic SDK with Kimi Code endpoint (api.kimi.com/coding)
  - moonshot: Uses OpenAI SDK (api.moonshot.cn/v1)

Single-pass pipeline:
  1. Build a structured prompt with market data, odds table, and optional web context
  2. Make one LLM call
  3. Parse XML-tagged sections from the response into ReportData
"""

from __future__ import annotations

import os
import re
from typing import Protocol

import openai

from kalshi_sports_edge.config import PROVIDER_BASE_URLS, PROVIDER_DEFAULT_MODELS, PROVIDER_ENV_KEYS
from kalshi_sports_edge.models import MarketData, OddsTable, ReportData


class LLMClient(Protocol):
    """Protocol for LLM clients (OpenAI or Anthropic compatible)."""

    def chat(self, system: str, user: str, max_tokens: int) -> str:
        """Send a chat request and return the response text."""
        ...


class OpenAIClientWrapper:
    """Wrapper around OpenAI SDK."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, model: str, system: str, user: str, max_tokens: int) -> str:
        resp = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


class AnthropicClientWrapper:
    """Wrapper around Anthropic SDK (also used by Kimi Code)."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url)

    def chat(self, model: str, system: str, user: str, max_tokens: int) -> str:
        import anthropic

        msg = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": user}],
            system=system,
        )
        # Handle content blocks - we expect TextBlock for standard responses
        first_block = msg.content[0]
        if isinstance(first_block, anthropic.types.TextBlock):
            return first_block.text
        return str(first_block)


def get_llm_client(provider: str) -> OpenAIClientWrapper | AnthropicClientWrapper:
    """Build an LLM client for the given provider.

    - claude: Anthropic SDK
    - kimi: Anthropic SDK with Kimi Code base URL
    - moonshot: OpenAI SDK

    Raises ValueError if the required API key env var is not set.
    """
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.environ.get(env_key)
    if not api_key:
        raise ValueError(
            f"Missing env var '{env_key}' required for provider '{provider}'. "
            f"Add it to your .env file."
        )

    base_url = PROVIDER_BASE_URLS.get(provider)

    if provider in ("claude", "kimi"):
        return AnthropicClientWrapper(api_key=api_key, base_url=base_url)
    return OpenAIClientWrapper(api_key=api_key, base_url=base_url)


def get_default_model(provider: str) -> str:
    return PROVIDER_DEFAULT_MODELS.get(provider, "claude-opus-4-6")


def run_single_pass(
    market: MarketData,
    odds_table: OddsTable,
    client: OpenAIClientWrapper | AnthropicClientWrapper,
    model: str,
    web_context: str | None = None,
    edge_threshold: float = 0.05,
) -> ReportData:
    """Run one LLM call and return a populated ReportData.

    The prompt uses XML tags to structure the response into parseable sections.
    Parsing is tolerant — missing sections result in None fields, not errors.
    """
    prompt = _build_prompt(market, odds_table, web_context, edge_threshold)
    try:
        raw = client.chat(
            model=model,
            system=_SYSTEM_PROMPT,
            user=prompt,
            max_tokens=1200,
        )
    except Exception as exc:
        # Handle both OpenAI and Anthropic error types
        error_str = str(exc).lower()
        if "401" in str(exc) or "authentication" in error_str:
            raise AuthenticationError(
                f"Authentication failed for {market.ticker}. "
                f"Check your API key is valid for the selected provider."
            ) from exc
        if "403" in str(exc) or "permission" in error_str:
            raise AuthenticationError(
                "Kimi Code API access denied (403). The kimi.com/code API may be "
                "restricted to approved coding agents. Try --provider moonshot instead, "
                "or obtain a standard Moonshot API key from https://platform.moonshot.cn"
            ) from exc
        raise
    return _parse_response(raw, market, odds_table, edge_threshold, web_context)


class AuthenticationError(Exception):
    """Raised when LLM API authentication fails."""


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
