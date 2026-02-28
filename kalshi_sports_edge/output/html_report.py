"""Single-page HTML consolidated report for kalshi_sports_edge.

Replaces the PDF consolidated report with a self-contained, browser-viewable
HTML file that includes all 8 sections, clear metric definitions, and
color-coded recommendations.

Output: reports/YYYY-MM-DD/consolidated_{HHMMSS}.html
"""

from __future__ import annotations

import datetime
import html as _html_escape
from pathlib import Path

from kalshi_sports_edge.models import MarketAnalysis

_EST_OFFSET = datetime.timezone(datetime.timedelta(hours=-5))


# ---------------------------------------------------------------------------
# Shared helpers (mirrors terminal.py / pdf_report.py)
# ---------------------------------------------------------------------------


def _e(s: object) -> str:
    """HTML-escape a value."""
    return _html_escape.escape(str(s))


def _fmt_game_time(iso_str: str | None) -> str:
    """Format estimated game start time (expiration − 3 h) as '~6:30 PM ET'."""
    if not iso_str:
        return "—"
    try:
        dt_utc = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        start_et = (dt_utc - datetime.timedelta(hours=3)).astimezone(_EST_OFFSET)
        hour = start_et.hour % 12 or 12
        am_pm = "AM" if start_et.hour < 12 else "PM"
        return f"~{hour}:{start_et.minute:02d} {am_pm} ET"
    except Exception:
        return "—"


def _fmt_vol(n: int) -> str:
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n}"


def _game_volumes(analyses: list[MarketAnalysis]) -> dict[str, int]:
    """event_ticker → combined volume across both sides of that game."""
    totals: dict[str, int] = {}
    for a in analyses:
        totals[a.market.event_ticker] = totals.get(a.market.event_ticker, 0) + a.market.volume
    return totals


def _by_volume_edge(a: MarketAnalysis) -> tuple:
    return (-a.market.volume, -abs(a.best_edge))


def _ensure_output_dir(output_dir: str) -> Path:
    path = Path(output_dir) / datetime.date.today().isoformat()
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_enhanced_consolidated_report(
    analyses: list[MarketAnalysis],
    generated_at: datetime.datetime,
    model: str,
    output_dir: str = "reports",
) -> Path:
    """Write a single-page HTML consolidated report. Returns the path."""
    ts = generated_at.strftime("%H%M%S")
    path = _ensure_output_dir(output_dir) / f"consolidated_{ts}.html"
    path.write_text(_build_html(analyses, generated_at, model), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------


def _build_html(
    analyses: list[MarketAnalysis],
    generated_at: datetime.datetime,
    model: str,
) -> str:
    game_vols = _game_volumes(analyses)
    sorted_all = sorted(analyses, key=_by_volume_edge)

    edge_picks = sorted(
        [a for a in analyses if abs(a.best_edge) >= 0.05],
        key=lambda x: abs(x.best_edge), reverse=True,
    )[:15]

    ev_picks = sorted(
        [a for a in analyses if a.best_ev > 0],
        key=lambda x: x.best_ev, reverse=True,
    )[:15]

    avoid = sorted(
        [a for a in analyses if abs(a.best_edge) < 0.05 or a.best_ev <= 0],
        key=_by_volume_edge,
    )[:10]

    n_with_edge = sum(1 for a in analyses if abs(a.best_edge) >= 0.05)
    top_pick = edge_picks[0] if edge_picks else None

    body_sections = "\n".join([
        _section_metrics_key(),
        _section_summary(sorted_all, game_vols),
        _section_top_edge(edge_picks, game_vols),
        _section_top_ev(ev_picks, game_vols),
        _section_avoid(avoid, game_vols),
        _section_mini_odds(sorted_all[:20], game_vols),
        _section_legend(),
    ])

    date_str = generated_at.strftime("%B %d, %Y %H:%M")
    top_edge_str = (
        f"{top_pick.market.title[:35]} ({top_pick.best_edge*100:+.1f}%)"
        if top_pick else "None"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Kalshi Sports Edge · {_e(generated_at.strftime('%Y-%m-%d'))}</title>
  <style>{_css()}</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="header-title">
      <span class="logo">📊</span>
      <div>
        <h1>Kalshi Sports Edge</h1>
        <p class="header-sub">Consolidated Deep-Research Report &nbsp;·&nbsp; {_e(date_str)} &nbsp;·&nbsp; {_e(model)}</p>
      </div>
    </div>
    <div class="header-stats">
      <div class="stat-card"><span class="stat-num">{len(analyses)}</span><span class="stat-label">Markets</span></div>
      <div class="stat-card green"><span class="stat-num">{n_with_edge}</span><span class="stat-label">With Edge ≥5%</span></div>
      <div class="stat-card blue"><span class="stat-num">{len(avoid)}</span><span class="stat-label">To Avoid</span></div>
    </div>
  </div>
  <nav class="toc">
    <a href="#metrics">📐 Metrics</a>
    <a href="#summary">📋 Summary</a>
    <a href="#top-edge">🎯 Top Edge</a>
    <a href="#top-ev">💰 Top EV</a>
    <a href="#avoid">⚠️ Avoid</a>
    <a href="#odds">🔢 Odds</a>
    <a href="#legend">📖 Legend</a>
  </nav>
  {f'<div class="top-pick-banner">🏆 Top Pick: <strong>{_e(top_edge_str)}</strong> &nbsp;·&nbsp; Side: <strong>{_e(top_pick.best_side)}</strong> &nbsp;·&nbsp; Confidence: <strong>{_e(top_pick.confidence)}</strong></div>' if top_pick else ''}
</header>

<div class="container">
{body_sections}

<footer>
  <p>Generated by Kalshi Sports Edge · {_e(date_str)} · Model: {_e(model)}</p>
  <p class="disclaimer">For informational purposes only. Prediction markets involve risk of loss. Past edge does not guarantee future results.</p>
</footer>
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _section_metrics_key() -> str:
    return """<section id="metrics">
  <h2>📐 How to Read the Metrics</h2>
  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-name">Edge</div>
      <div class="metric-formula">LLM probability − Market implied probability</div>
      <div class="metric-desc">How much the LLM thinks the market is mispriced. <strong>+10%</strong> means the LLM estimates the true probability is 10 percentage points higher than the market price implies. A meaningful edge threshold is ≥ 5%.</div>
    </div>
    <div class="metric-card">
      <div class="metric-name">EV <span class="unit">(per $1 wagered)</span></div>
      <div class="metric-formula">Edge ÷ Implied probability</div>
      <div class="metric-desc">Expected profit per dollar wagered, accounting for cost of the bet. A 10% edge on a 45¢ contract gives EV = 0.10 ÷ 0.45 = <strong>+$0.22</strong> per $1 risked. Higher price = lower EV for the same edge.</div>
    </div>
    <div class="metric-card">
      <div class="metric-name">ROI <span class="unit">(%)</span></div>
      <div class="metric-formula">EV × 100</div>
      <div class="metric-desc">Expected return as a percentage of your stake. EV = +0.22 → ROI = <strong>+22%</strong>. Normalises across contracts of different prices. Same edge on a cheap underdog has much higher ROI than on a favourite.</div>
    </div>
    <div class="metric-card">
      <div class="metric-name">Game Vol</div>
      <div class="metric-formula">Sum of volume across both sides of the same game</div>
      <div class="metric-desc">Total contracts traded for this matchup (both team's YES markets combined). Higher volume = more informed market pricing = edge signals are more credible.</div>
    </div>
    <div class="metric-card">
      <div class="metric-name">YES¢ / NO¢</div>
      <div class="metric-formula">Mid-price of YES contract / Mid-price of NO contract</div>
      <div class="metric-desc">The cost in cents to buy a $1 YES or NO contract. Always sums to ~100¢. Buying YES at 45¢ implies the market thinks there's a 45% chance of YES winning.</div>
    </div>
    <div class="metric-card">
      <div class="metric-name">Best Side</div>
      <div class="metric-formula">The outcome with the highest edge</div>
      <div class="metric-desc">Whether to BUY YES or BUY NO. Since YES + NO always sum to 1, exactly one side always has a positive edge when the LLM disagrees with the market. "BUY NO" = market overprices YES.</div>
    </div>
  </div>
</section>"""


def _section_summary(analyses: list[MarketAnalysis], game_vols: dict[str, int]) -> str:
    rows = ""
    for i, a in enumerate(analyses[:30]):
        gv = _fmt_vol(game_vols.get(a.market.event_ticker, a.market.volume))
        t = _fmt_game_time(a.market.expected_expiration_time)
        gd = a.market.game_date.strftime("%b %d") if a.market.game_date else "—"
        yes_p = a.odds_table.yes_row.price_cents
        no_p = a.odds_table.no_row.price_cents
        edge_cls = _edge_cls(a.best_edge)
        rec, rec_cls = _rec(a.best_edge)
        sent_cls = "sent-bull" if a.sentiment == "Bullish" else ("sent-bear" if a.sentiment == "Bearish" else "sent-neut")
        rows += f"""<tr class="{'row-alt' if i % 2 else ''}">
  <td class="market-name" title="{_e(a.market.ticker)}">{_e(a.market.title[:38])}</td>
  <td class="date-chip">{_e(gd)}</td>
  <td>{_e(t)}</td>
  <td class="vol">{_e(gv)}</td>
  <td class="price-badge">{yes_p}¢ / {no_p}¢</td>
  <td class="side-badge">{_e(a.best_side)}</td>
  <td class="{edge_cls}">{a.best_edge*100:+.1f}%</td>
  <td class="{edge_cls}">{a.best_ev:+.3f}</td>
  <td class="{edge_cls}">{a.best_roi:+.1f}%</td>
  <td class="{sent_cls}">{_e(a.sentiment)}</td>
  <td><span class="badge {rec_cls}">{rec}</span></td>
  <td class="conf-{a.confidence.lower()}">{_e(a.confidence)}</td>
  <td class="reason">{_e(a.reason)}</td>
</tr>"""
    return f"""<section id="summary">
  <h2>📋 All Markets — Summary Table</h2>
  <p class="section-note">Sorted by game volume (most liquid first). Edge ≥ 5% is highlighted green.</p>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th title="Market title">Market</th>
      <th title="Game date">Date</th>
      <th title="Estimated tip-off / start time ET">Time ET</th>
      <th title="Combined volume for this matchup (both sides)">Game Vol</th>
      <th title="YES mid-price / NO mid-price in cents">YES¢ / NO¢</th>
      <th title="Which side has the better edge (BUY YES or BUY NO)">Side</th>
      <th title="Edge = LLM probability − market implied probability">Edge</th>
      <th title="EV per $1 wagered = Edge ÷ Implied probability">EV/$1</th>
      <th title="Return on investment as a percentage of stake">ROI%</th>
      <th title="Market sentiment based on edge magnitude">Sentiment</th>
      <th title="Recommendation based on edge threshold of 5%">Rec</th>
      <th title="LLM confidence after considering volume and web context">Conf</th>
      <th title="Primary reason for the LLM estimate">Why</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</section>"""


def _section_top_edge(picks: list[MarketAnalysis], game_vols: dict[str, int]) -> str:
    if not picks:
        return """<section id="top-edge"><h2>🎯 Top Picks by Edge</h2>
  <p class="empty-note">No markets with |Edge| ≥ 5% found.</p></section>"""
    rows = ""
    for i, a in enumerate(picks):
        gv = _fmt_vol(game_vols.get(a.market.event_ticker, a.market.volume))
        t = _fmt_game_time(a.market.expected_expiration_time)
        gd = a.market.game_date.strftime("%b %d") if a.market.game_date else "—"
        yes_p = a.odds_table.yes_row.price_cents
        no_p = a.odds_table.no_row.price_cents
        market_pct = (a.market_yes_implied if a.best_side == "YES" else a.market_no_implied)
        llm_pct = (a.llm_yes_prob if a.best_side == "YES" else a.llm_no_prob)
        rows += f"""<tr class="{'row-alt' if i % 2 else ''}">
  <td class="rank">#{i+1}</td>
  <td class="market-name" title="{_e(a.market.ticker)}">{_e(a.market.title[:40])}</td>
  <td class="date-chip">{_e(gd)}</td>
  <td>{_e(t)}</td>
  <td class="vol">{_e(gv)}</td>
  <td class="price-badge">{yes_p}¢ / {no_p}¢</td>
  <td class="side-badge">{_e(a.best_side)}</td>
  <td class="prob-mkt">{market_pct:.1%}</td>
  <td class="prob-llm">{llm_pct:.1%}</td>
  <td class="edge-pos">{a.best_edge*100:+.1f}%</td>
  <td class="edge-pos">{a.best_ev:+.3f}</td>
  <td class="edge-pos">{a.best_roi:+.1f}%</td>
  <td class="conf-{a.confidence.lower()}">{_e(a.confidence)}</td>
  <td class="reason">{_e(a.reason)}</td>
</tr>"""
    return f"""<section id="top-edge">
  <h2>🎯 Top Picks by Edge <span class="badge badge-green">|Edge| ≥ 5%</span></h2>
  <p class="section-note">Ranked by absolute edge. "Market %" = current market implied probability for the recommended side. "LLM %" = LLM's true-probability estimate. Difference is the Edge.</p>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>#</th>
      <th>Market</th>
      <th>Date</th>
      <th>Time ET</th>
      <th title="Combined volume both sides">Game Vol</th>
      <th>YES¢ / NO¢</th>
      <th title="Recommended side">Side</th>
      <th title="Market implied probability for the recommended side">Market %</th>
      <th title="LLM estimated true probability for the recommended side">LLM %</th>
      <th title="LLM% − Market% for the recommended side">Edge</th>
      <th title="Edge ÷ Implied probability">EV/$1</th>
      <th title="EV × 100">ROI%</th>
      <th>Conf</th>
      <th>Why</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</section>"""


def _section_top_ev(picks: list[MarketAnalysis], game_vols: dict[str, int]) -> str:
    if not picks:
        return """<section id="top-ev"><h2>💰 Top Picks by EV</h2>
  <p class="empty-note">No markets with positive EV found.</p></section>"""
    rows = ""
    for i, a in enumerate(picks):
        gv = _fmt_vol(game_vols.get(a.market.event_ticker, a.market.volume))
        t = _fmt_game_time(a.market.expected_expiration_time)
        gd = a.market.game_date.strftime("%b %d") if a.market.game_date else "—"
        yes_p = a.odds_table.yes_row.price_cents
        no_p = a.odds_table.no_row.price_cents
        rows += f"""<tr class="{'row-alt' if i % 2 else ''}">
  <td class="rank">#{i+1}</td>
  <td class="market-name" title="{_e(a.market.ticker)}">{_e(a.market.title[:40])}</td>
  <td class="date-chip">{_e(gd)}</td>
  <td>{_e(t)}</td>
  <td class="vol">{_e(gv)}</td>
  <td class="price-badge">{yes_p}¢ / {no_p}¢</td>
  <td class="side-badge">{_e(a.best_side)}</td>
  <td class="edge-pos">{a.best_ev:+.3f}</td>
  <td class="edge-pos">{a.best_roi:+.1f}%</td>
  <td class="edge-pos">{a.best_edge*100:+.1f}%</td>
  <td class="conf-{a.confidence.lower()}">{_e(a.confidence)}</td>
</tr>"""
    return f"""<section id="top-ev">
  <h2>💰 Top Picks by EV <span class="badge badge-blue">Positive EV</span></h2>
  <p class="section-note">Ranked by EV per $1 wagered. A higher EV means better return relative to the cost of the bet. Cheap underdog contracts amplify EV even with moderate edge.</p>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>#</th>
      <th>Market</th>
      <th>Date</th>
      <th>Time ET</th>
      <th>Game Vol</th>
      <th>YES¢ / NO¢</th>
      <th>Side</th>
      <th title="Edge ÷ Implied probability — expected profit per dollar wagered">EV/$1</th>
      <th title="EV × 100 — return as % of stake">ROI%</th>
      <th title="LLM% − Market% for the recommended side">Edge</th>
      <th>Conf</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</section>"""


def _section_avoid(avoid: list[MarketAnalysis], game_vols: dict[str, int]) -> str:
    if not avoid:
        return """<section id="avoid"><h2>⚠️ Markets to Avoid</h2>
  <p class="empty-note">All markets show meaningful edge — no avoids.</p></section>"""
    rows = ""
    for i, a in enumerate(avoid):
        gv = _fmt_vol(game_vols.get(a.market.event_ticker, a.market.volume))
        t = _fmt_game_time(a.market.expected_expiration_time)
        gd = a.market.game_date.strftime("%b %d") if a.market.game_date else "—"
        yes_p = a.odds_table.yes_row.price_cents
        no_p = a.odds_table.no_row.price_cents
        # Explain why it's an avoid
        if abs(a.best_edge) < 0.01:
            why = "Flat — LLM agrees with market"
        elif abs(a.best_edge) < 0.03:
            why = "Tiny edge — noise territory"
        elif a.market.volume < 500:
            why = "Low liquidity — unreliable"
        else:
            why = "Edge below 5% threshold"
        rows += f"""<tr class="{'row-alt' if i % 2 else ''}">
  <td class="market-name" title="{_e(a.market.ticker)}">{_e(a.market.title[:40])}</td>
  <td class="date-chip">{_e(gd)}</td>
  <td>{_e(t)}</td>
  <td class="vol">{_e(gv)}</td>
  <td class="price-badge">{yes_p}¢ / {no_p}¢</td>
  <td class="edge-low">{a.best_edge*100:+.1f}%</td>
  <td class="edge-low">{a.best_ev:+.3f}</td>
  <td class="reason">{_e(why)}</td>
  <td class="conf-{a.confidence.lower()}">{_e(a.confidence)}</td>
</tr>"""
    return f"""<section id="avoid">
  <h2>⚠️ Markets to Avoid <span class="badge badge-red">|Edge| &lt; 5%</span></h2>
  <p class="section-note">Markets where the LLM's estimate is too close to the market price to warrant a bet. The "Why" column explains the specific reason.</p>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Market</th>
      <th>Date</th>
      <th>Time ET</th>
      <th>Game Vol</th>
      <th>YES¢ / NO¢</th>
      <th title="Best edge across both sides">Best Edge</th>
      <th title="Expected value per $1 wagered">EV/$1</th>
      <th>Reason to Avoid</th>
      <th>Conf</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</section>"""


def _section_mini_odds(analyses: list[MarketAnalysis], game_vols: dict[str, int]) -> str:
    cards = ""
    for a in analyses:
        gv = _fmt_vol(game_vols.get(a.market.event_ticker, a.market.volume))
        t = _fmt_game_time(a.market.expected_expiration_time)
        gd = a.market.game_date.strftime("%B %d, %Y") if a.market.game_date else "—"
        yes_p = a.odds_table.yes_row.price_cents
        no_p = a.odds_table.no_row.price_cents
        rec, rec_cls = _rec(a.best_edge)

        yes_ecls = "edge-pos" if a.yes_edge >= 0.05 else ("edge-neg" if a.yes_edge <= -0.05 else "edge-low")
        no_ecls = "edge-pos" if a.no_edge >= 0.05 else ("edge-neg" if a.no_edge <= -0.05 else "edge-low")

        yes_team = _e(a.market.yes_team or "YES")
        no_team = _e(a.market.no_team or "NO")

        cards += f"""<div class="odds-card">
  <div class="odds-card-header">
    <div class="odds-card-title">{_e(a.market.title)}</div>
    <div class="odds-card-meta">
      <span class="date-chip">{_e(gd)}</span>
      <span>{_e(t)}</span>
      <span class="vol">Game Vol: {_e(gv)}</span>
      <span><span class="badge {rec_cls}">{rec} {_e(a.best_side)}</span></span>
      <span class="conf-{a.confidence.lower()}">Conf: {_e(a.confidence)}</span>
    </div>
  </div>
  <table class="odds-inner">
    <thead><tr>
      <th>Outcome</th>
      <th title="Current market mid-price in cents">Price (¢)</th>
      <th title="Market implied probability = price ÷ 100">Market Implied</th>
      <th title="LLM estimated true probability">LLM Estimate</th>
      <th title="LLM% − Market% = mispricing signal">Edge</th>
      <th title="Edge ÷ Implied">EV/$1</th>
      <th title="EV × 100">ROI%</th>
    </tr></thead>
    <tbody>
      <tr class="{'row-best' if a.best_side=='YES' else ''}">
        <td class="team-name">{yes_team} <span class="outcome-badge">YES</span></td>
        <td class="price">{yes_p}¢</td>
        <td>{a.market_yes_implied:.1%}</td>
        <td class="{'prob-llm' if a.yes_edge >= 0.05 else ''}">{a.llm_yes_prob:.1%}</td>
        <td class="{yes_ecls}">{a.yes_edge*100:+.1f}%</td>
        <td class="{yes_ecls}">{a.yes_ev:+.3f}</td>
        <td class="{yes_ecls}">{a.yes_roi:+.1f}%</td>
      </tr>
      <tr class="{'row-best' if a.best_side=='NO' else ''}">
        <td class="team-name">{no_team} <span class="outcome-badge">NO</span></td>
        <td class="price">{no_p}¢</td>
        <td>{a.market_no_implied:.1%}</td>
        <td class="{'prob-llm' if a.no_edge >= 0.05 else ''}">{a.llm_no_prob:.1%}</td>
        <td class="{no_ecls}">{a.no_edge*100:+.1f}%</td>
        <td class="{no_ecls}">{a.no_ev:+.3f}</td>
        <td class="{no_ecls}">{a.no_roi:+.1f}%</td>
      </tr>
    </tbody>
  </table>
  <div class="llm-analysis">{_e(a.llm_analysis[:300])}{'…' if len(a.llm_analysis) > 300 else ''}</div>
</div>"""

    return f"""<section id="odds">
  <h2>🔢 Mini Odds Overview — Per Market</h2>
  <p class="section-note">Highlighted row = recommended side. Green edge = LLM sees an edge; red = market overprices that side.</p>
  <div class="odds-cards">{cards}</div>
</section>"""


def _section_legend() -> str:
    items = [
        ("stats", "Team/player statistics drove the estimate"),
        ("injury", "Player injury status is the key variable"),
        ("form", "Recent form/performance trend is decisive"),
        ("news", "Breaking news materially changes the outlook"),
        ("data", "Market or historical base-rate data used"),
        ("record", "Head-to-head record is the main reference"),
        ("consensus", "Expert or public consensus is the anchor"),
        ("volume", "Trading volume signals informed positioning"),
        ("schedule", "Schedule strength or matchup context"),
        ("weather", "Weather/field conditions are the swing factor"),
        ("momentum", "Recent momentum swing is the key signal"),
        ("unclear", "Insufficient information to be confident"),
    ]
    legend_html = "".join(
        f'<div class="legend-item"><code>{_e(k)}</code><span>{_e(v)}</span></div>'
        for k, v in items
    )
    return f"""<section id="legend">
  <h2>📖 Why Column Legend</h2>
  <div class="legend-grid">{legend_html}</div>
</section>"""


# ---------------------------------------------------------------------------
# Shared cell helpers
# ---------------------------------------------------------------------------


def _rec(best_edge: float) -> tuple[str, str]:
    if best_edge >= 0.05:
        return "BUY", "badge-green"
    if best_edge <= -0.05:
        return "SELL", "badge-red"
    return "HOLD", "badge-gray"


def _edge_cls(best_edge: float) -> str:
    if best_edge >= 0.05:
        return "edge-pos"
    if best_edge <= -0.05:
        return "edge-neg"
    return "edge-low"


def _build_footer() -> str:
    return ""  # embedded in _build_html


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _css() -> str:
    return """
:root {
  --navy: #1a237e;
  --blue: #1565c0;
  --blue-lt: #e3f2fd;
  --green: #1b5e20;
  --green-lt: #e8f5e9;
  --green-mid: #2e7d32;
  --red: #b71c1c;
  --red-lt: #ffebee;
  --amber: #e65100;
  --amber-lt: #fff3e0;
  --gray: #546e7a;
  --gray-lt: #f5f7f9;
  --border: #e0e0e0;
  --text: #212121;
  --text-sm: #616161;
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font);
  color: var(--text);
  background: #f0f2f5;
  font-size: 14px;
  line-height: 1.5;
}

/* ── HEADER ─────────────────────────────── */
header {
  background: linear-gradient(135deg, var(--navy) 0%, #283593 60%, var(--blue) 100%);
  color: white;
  padding: 0;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,.35);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px 10px;
  flex-wrap: wrap;
  gap: 12px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo { font-size: 28px; }
h1 { font-size: 20px; font-weight: 700; letter-spacing: .3px; }
.header-sub { font-size: 12px; opacity: .8; margin-top: 2px; }

.header-stats { display: flex; gap: 10px; }
.stat-card {
  background: rgba(255,255,255,.15);
  border-radius: 8px;
  padding: 6px 14px;
  text-align: center;
  min-width: 70px;
}
.stat-card.green { background: rgba(56,142,60,.45); }
.stat-card.blue  { background: rgba(100,181,246,.3); }
.stat-num   { display: block; font-size: 20px; font-weight: 700; }
.stat-label { display: block; font-size: 10px; opacity: .85; }

.toc {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  padding: 0 20px 8px;
}
.toc a {
  color: rgba(255,255,255,.85);
  text-decoration: none;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  transition: background .15s;
}
.toc a:hover { background: rgba(255,255,255,.2); color: white; }

.top-pick-banner {
  background: rgba(255,193,7,.18);
  border-top: 1px solid rgba(255,193,7,.4);
  padding: 6px 24px;
  font-size: 12.5px;
  color: rgba(255,255,255,.95);
}

/* ── CONTAINER ─────────────────────────── */
.container { max-width: 1300px; margin: 0 auto; padding: 20px 16px 40px; }

/* ── SECTIONS ─────────────────────────── */
section {
  background: white;
  border-radius: 10px;
  padding: 22px 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.09);
}

section h2 {
  font-size: 16px;
  font-weight: 700;
  color: var(--navy);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-note {
  font-size: 12px;
  color: var(--text-sm);
  margin-bottom: 12px;
  line-height: 1.45;
}

.empty-note {
  color: var(--text-sm);
  font-style: italic;
  padding: 12px 0;
}

/* ── METRICS GRID ─────────────────────── */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-top: 8px;
}

.metric-card {
  background: var(--gray-lt);
  border: 1px solid var(--border);
  border-left: 4px solid var(--blue);
  border-radius: 8px;
  padding: 12px 14px;
}

.metric-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--navy);
  margin-bottom: 2px;
}

.metric-name .unit { font-weight: 400; font-size: 11px; color: var(--gray); }

.metric-formula {
  font-size: 11px;
  font-family: monospace;
  color: var(--blue);
  margin-bottom: 5px;
  background: #e3f2fd;
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
}

.metric-desc { font-size: 12px; color: var(--text-sm); line-height: 1.45; }

/* ── TABLES ─────────────────────────────  */
.table-wrap {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

thead tr { background: var(--navy); }
thead th {
  color: white;
  text-align: left;
  padding: 9px 10px;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: .3px;
  white-space: nowrap;
  cursor: default;
}
thead th[title] { border-bottom: 1px dotted rgba(255,255,255,.4); }

tbody tr { border-bottom: 1px solid var(--border); transition: background .1s; }
tbody tr:hover { background: #f0f4ff; }
.row-alt { background: #fafbff; }
tbody td { padding: 7px 10px; vertical-align: middle; }

/* ── CELL CLASSES ────────────────────── */
.market-name { font-weight: 600; max-width: 260px; }
.rank { font-weight: 700; color: var(--navy); text-align: center; }
.vol  { font-weight: 600; color: var(--text-sm); white-space: nowrap; }

.date-chip {
  display: inline-block;
  background: var(--blue-lt);
  color: var(--blue);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  white-space: nowrap;
}

.price-badge {
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--navy);
  white-space: nowrap;
}

.side-badge {
  font-weight: 700;
  color: var(--green-mid);
  text-align: center;
}

.edge-pos { color: var(--green-mid); font-weight: 700; }
.edge-neg { color: var(--red);       font-weight: 700; }
.edge-low { color: var(--gray);      font-weight: 500; }

.prob-mkt { color: var(--text-sm); }
.prob-llm { color: var(--blue); font-weight: 600; }

.sent-bull { color: var(--green-mid); font-weight: 600; }
.sent-bear { color: var(--red);       font-weight: 600; }
.sent-neut { color: var(--gray); }

.conf-high   { color: var(--navy);      font-weight: 600; }
.conf-medium { color: var(--gray); }
.conf-low    { color: #9e9e9e;    font-style: italic; }

.reason { font-size: 11px; color: var(--text-sm); font-style: italic; }

/* ── BADGES ─────────────────────────── */
.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .3px;
  white-space: nowrap;
}
.badge-green { background: var(--green-lt);  color: var(--green-mid); border: 1px solid #a5d6a7; }
.badge-red   { background: var(--red-lt);    color: var(--red);       border: 1px solid #ef9a9a; }
.badge-blue  { background: var(--blue-lt);   color: var(--blue);      border: 1px solid #90caf9; }
.badge-gray  { background: #eeeeee;          color: var(--gray);      border: 1px solid #bdbdbd; }

/* ── ODDS CARDS ─────────────────────── */
.odds-cards { display: flex; flex-direction: column; gap: 16px; }

.odds-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

.odds-card-header {
  background: var(--gray-lt);
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}

.odds-card-title {
  font-weight: 700;
  font-size: 14px;
  color: var(--navy);
  margin-bottom: 5px;
}

.odds-card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-sm);
}

.odds-inner { border-radius: 0; }
.odds-inner thead tr { background: #37474f; }

.row-best { background: #e8f5e9 !important; }
.row-best:hover { background: #c8e6c9 !important; }

.team-name { font-weight: 600; min-width: 120px; }

.outcome-badge {
  font-size: 9px;
  background: var(--blue-lt);
  color: var(--blue);
  padding: 1px 5px;
  border-radius: 6px;
  font-weight: 700;
  vertical-align: middle;
}

.price { font-family: monospace; font-weight: 700; font-size: 13px; }

.llm-analysis {
  padding: 8px 14px;
  font-size: 12px;
  color: var(--text-sm);
  background: #fafafa;
  border-top: 1px solid var(--border);
  font-style: italic;
  line-height: 1.5;
}

/* ── LEGEND ─────────────────────────── */
.legend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.legend-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  padding: 5px 0;
}

.legend-item code {
  background: var(--blue-lt);
  color: var(--navy);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  min-width: 80px;
  display: inline-block;
}

/* ── FOOTER ─────────────────────────── */
footer {
  text-align: center;
  padding: 24px 16px;
  font-size: 12px;
  color: var(--text-sm);
}
.disclaimer { margin-top: 4px; font-size: 11px; opacity: .7; }

@media (max-width: 768px) {
  .header-inner { flex-direction: column; align-items: flex-start; }
  .header-stats { flex-wrap: wrap; }
  .metrics-grid { grid-template-columns: 1fr; }
  .table-wrap { font-size: 11px; }
}
"""
