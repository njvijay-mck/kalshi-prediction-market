# Kalshi Sports Edge - Design & Implementation Specification

> **Purpose:** This document provides comprehensive design and implementation details for the `kalshi_sports_edge` module. It is intended for AI assistants and developers who need to understand the architecture, modify code, or extend functionality.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [Sports Categories](#sports-categories)
5. [Market Fetching Strategy](#market-fetching-strategy)
6. [Deep Research Pipeline](#deep-research-pipeline)
7. [Web Search Implementation](#web-search-implementation)
8. [Metrics Calculation](#metrics-calculation)
9. [Report Generation](#report-generation)
10. [CLI Interface](#cli-interface)
11. [Extension Points](#extension-points)

---

## Overview

### What is Kalshi Sports Edge?

A professional-grade sports prediction market analysis tool that:
- Fetches live sports markets from Kalshi API
- Performs multi-source web research (Reddit, Yahoo, ESPN, X/Twitter)
- Uses Large Language Models (LLM) to estimate true probabilities
- Calculates Edge, Expected Value (EV), and Return on Investment (ROI)
- Generates professional consolidated reports (terminal + PDF)

### Key Features

- **6 Sports Categories:** Basketball, Football, Baseball, Soccer, Tennis, Hockey
- **106 Sports Series:** From NBA to Champions League to ATP Tennis
- **Multi-Source Web Search:** Parallel searches across 5 sources
- **5-Stage Deep Research Pipeline:** Web → Probability → Metrics → Classification → Consolidation
- **8-Section Report Format:** Comprehensive analysis output
- **Professional PDF Output:** Styled reports with color coding

---

## Architecture

### Module Structure

```
kalshi_sports_edge/
├── __init__.py           # Package initialization
├── __main__.py           # Entry point for `python -m kalshi_sports_edge`
├── cli.py                # CLI argument parsing and validation
├── config.py             # Configuration constants, sports categories
├── models.py             # Dataclasses for all data structures
├── orchestrator.py       # Main coordinator, workflow orchestration
├── output/
│   ├── __init__.py
│   ├── pdf_report.py     # PDF generation with reportlab
│   └── terminal.py       # Rich terminal output formatting
└── services/
    ├── __init__.py
    ├── deep_research.py  # 5-stage analysis pipeline
    ├── llm_pipeline.py   # Single-pass LLM analysis
    ├── market_fetcher.py # Kalshi API market fetching
    ├── market_utils.py   # Market grouping utilities
    ├── odds_engine.py    # Odds/probability calculations
    └── web_search.py     # Multi-source Brave search
```

### Data Flow

```
User Input (CLI)
    ↓
CLI Parser (cli.py)
    ↓
Orchestrator (orchestrator.py)
    ├── Market Fetcher → Kalshi API → MarketData[]
    ├── Odds Engine → OddsTable[]
    │
    ├── [Single-Pass Mode]
    │   └── LLM Pipeline → ReportData[]
    │
    └── [Deep Research Mode]
        ├── Web Search → MultiSourceContext
        ├── Deep Research → MarketAnalysis[]
        │   ├── Probability Estimation
        │   ├── Edge/EV/ROI Calculation
        │   └── Classification
        └── Report Generation
            ├── Terminal Output
            └── PDF Output
```

---

## Data Models

### MarketData

Represents a single Kalshi market.

```python
@dataclass
class MarketData:
    ticker: str                    # e.g., "KXNBAGAME-26FEB24BOSPHX-BOS"
    title: str                     # e.g., "Boston at Phoenix Winner?"
    event_ticker: str              # e.g., "KXNBAGAME-26FEB24BOSPHX"
    category: str | None           # "Sports" or None
    tags: list[str]                # Market tags
    status: str                    # "open", "closed", etc.
    
    # Pricing
    yes_bid: int | None            # Bid price in cents (1-99)
    yes_ask: int | None            # Ask price in cents (1-99)
    last_price: int | None         # Last traded price
    
    # Volume
    volume: int                    # Contracts traded
    open_interest: int             # Open contracts
    
    # Timing
    close_time: str | None         # ISO8601 settlement deadline
    game_date: datetime.date | None  # Parsed from event_ticker
    expected_expiration_time: str | None  # Proxy for game end
    
    # Teams
    yes_team: str | None           # Team name for YES outcome
    no_team: str | None            # Team name for NO outcome
    
    # Computed Properties
    @property
    def mid_price(self) -> int | None  # (yes_bid + yes_ask) // 2
    @property
    def spread_cents(self) -> int | None  # yes_ask - yes_bid
    def game_start_time(self) -> datetime.datetime | None
    def has_started(self) -> bool
```

### OddsTable

Complete odds analysis for one market.

```python
@dataclass
class OddsTable:
    market: MarketData
    yes_row: OddsRow
    no_row: OddsRow
    overround: float               # (yes_implied + no_implied) - 1.0
    price_source: str              # "mid" | "last" | "ask" | "bid"
    wide_spread: bool              # True if spread > threshold

@dataclass
class OddsRow:
    outcome: str                   # "YES" or "NO"
    price_cents: int               # 1-99
    implied_prob: float            # price_cents / 100.0
    decimal_odds: float            # 100.0 / price_cents
    american_odds: int             # Moneyline format
    fractional_str: str            # e.g., "4/1" or "1/4"
    edge: float | None = None      # Filled after LLM analysis
```

### MarketAnalysis (Deep Research)

Comprehensive analysis including LLM probabilities and metrics.

```python
@dataclass
class MarketAnalysis:
    # Source data
    market: MarketData
    odds_table: OddsTable
    
    # LLM-estimated true probabilities (0-1)
    llm_yes_prob: float
    llm_no_prob: float
    
    # Calculated metrics
    yes_edge: float                # llm_yes_prob - market_yes_implied
    no_edge: float                 # llm_no_prob - market_no_implied
    yes_ev: float                  # Expected value per cent for YES
    no_ev: float                   # Expected value per cent for NO
    yes_roi: float                 # Return on investment % for YES
    no_roi: float                  # Return on investment % for NO
    
    # Best side (highest edge)
    best_edge: float
    best_ev: float
    best_side: str                 # "YES" or "NO"
    best_roi: float
    
    # Classification
    sentiment: str                 # "Bullish", "Neutral", "Bearish"
    confidence: str                # "High", "Medium", "Low"
    reason: str                    # "stats", "injury", "form", etc.
    
    # Context and analysis
    web_context: str               # Aggregated web search results
    llm_analysis: str              # LLM analysis text
```

### ConsolidatedReport

Final report from deep research pipeline.

```python
@dataclass
class ConsolidatedReport:
    generated_at: datetime.datetime
    markets: list[MarketData]
    odds_tables: list[OddsTable]
    research_output: str | None
    critique_output: str | None
    rebuttal_output: str | None
    consolidation_output: str | None
    metrics: RunMetrics | None
    # Attached dynamically:
    _analyses: list[MarketAnalysis]  # For enhanced output
```

---

## Sports Categories

### Configuration Structure (config.py)

Sports are organized by category for filtering and fetching:

```python
SPORT_CATEGORIES: dict[str, list[str]] = {
    "basketball": BASKETBALL_SERIES,  # 19 series
    "football": FOOTBALL_SERIES,      # 3 series
    "baseball": BASEBALL_SERIES,      # 2 series
    "soccer": SOCCER_SERIES,          # 39 series
    "tennis": TENNIS_SERIES,          # 38 series
    "hockey": HOCKEY_SERIES,          # 5 series
}
```

### Series Ticker Naming Convention

Kalshi uses consistent prefixes for sports series:

| Sport | Prefix Pattern | Example |
|-------|---------------|---------|
| NBA | `KXNBAGAME` | `KXNBAGAME-26FEB24BOSPHX` |
| NFL | `KXNFLGAME` | `KXNFLGAME-26FEB24KCPHI` |
| MLB | `KXMLBGAME` | `KXMLBGAME-26FEB24NYMBOL` |
| NHL | `KXNHLGAME` | `KXNHLGAME-26FEB24TORBOS` |
| NCAA Basketball | `KXNCAAMBGAME` | `KXNCAAMBGAME-26FEB24DUKEND` |
| MLS | `KXMLSGAME` | `KXMLSGAME-26FEB24ATXHOU` |
| EPL | `KXEPLGAME` | `KXEPLGAME-26FEB24EVEMUN` |
| ATP Tennis | `KXATPMATCH` | `KXATPMATCH-26FEB24ALCRUB` |

---

## Market Fetching Strategy

### Challenge

The flat `/markets` endpoint returns parlay markets first, burying individual game markets. The solution is to use `/events?series_ticker=X` for each known sports series.

### Implementation (market_fetcher.py)

```python
def _fetch_all_sports_markets(sports: list[str] | None = None) -> list[MarketData]:
    """
    1. Determine series to fetch from SPORT_CATEGORIES
    2. For each series:
       - Call GET /events?series_ticker=<series>&status=open&with_nested_markets=true
       - Paginate through all pages
       - Extract markets from each event
    3. Deduplicate by ticker
    4. Return complete list
    """
```

### Fetch Functions

| Function | Purpose |
|----------|---------|
| `fetch_by_ticker(ticker)` | Single market lookup |
| `fetch_by_keyword(query, ...)` | Search by keyword in title/ticker |
| `fetch_by_date(game_date, ...)` | Filter by game date |
| `fetch_top_n(n, ...)` | Top N by volume |
| `_fetch_all_sports_markets(...)` | Fetch all markets from selected sports |

### Date Parsing

Game dates are extracted from event tickers:
- Format: `KXNBAGAME-26FEB24BOSPHX`
- Pattern: `YY` + `MON` + `DD` → `26FEB24`
- Parsed to: `datetime.date(2026, 2, 24)`

---

## Deep Research Pipeline

### Overview

5-stage pipeline for comprehensive market analysis:

```
Stage 1: Web Research
    ↓
Stage 2: Probability Estimation
    ↓
Stage 3: Edge/EV/ROI Calculation
    ↓
Stage 4: Classification
    ↓
Stage 5: Consolidation
```

### Stage 1: Web Research

**File:** `services/web_search.py`

**Sources Searched (in parallel):**

| Source | Query Pattern |
|--------|---------------|
| Reddit | `site:reddit.com/r/nba {team_a} vs {team_b}` |
| Yahoo Sports | `site:sports.yahoo.com {team_a} vs {team_b}` |
| ESPN | `site:espn.com {team_a} {team_b} preview` |
| X/Twitter | `site:twitter.com OR site:x.com {team_a} {team_b} prediction` |
| General | `{team_a} vs {team_b} prediction odds` |

**Output:** `MultiSourceContext` with aggregated results

### Stage 2: Probability Estimation

**File:** `services/deep_research.py` → `_estimate_probabilities()`

**Process:**
1. Build prompt with market data + web context
2. LLM call with system prompt: "You are an expert sports analyst"
3. Parse response for:
   - `<analysis>`: Key factors (form, injuries, matchups)
   - `<probabilities>`: YES: XX.X%, NO: XX.X%
   - `<confidence>`: Level + Reason

**Prompt Template:**
```
Analyze this sports prediction market using the provided web research context.

**Market:** {title}
**Current Market Prices:**
- YES ({team_a}): {yes_price}¢ (implied {yes_implied}%)
- NO ({team_b}): {no_price}¢ (implied {no_implied}%)

{web_context}

Based on the web research, estimate TRUE probabilities for YES and NO outcomes.
```

### Stage 3: Edge/EV/ROI Calculation

**Formulas:**

```python
# Edge (percentage points)
yes_edge = llm_yes_prob - market_yes_implied
no_edge = llm_no_prob - market_no_implied

# Expected Value (per cent)
yes_ev = yes_edge  # EV = TrueProb - MarketImplied = Edge
no_ev = no_edge

# Return on Investment (%)
yes_roi = (yes_ev / yes_market_price) * 100
no_roi = (no_ev / no_market_price) * 100

# Best side selection
if yes_edge >= no_edge:
    best_edge, best_ev, best_side, best_roi = yes_edge, yes_ev, "YES", yes_roi
else:
    best_edge, best_ev, best_side, best_roi = no_edge, no_ev, "NO", no_roi
```

### Stage 4: Classification

**Sentiment Classification:**
```python
if best_edge >= 0.05:
    sentiment = "Bullish"
elif best_edge <= -0.05:
    sentiment = "Bearish"
else:
    sentiment = "Neutral"
```

**Confidence Level:**
- Determined by LLM self-assessment
- Adjusted based on volume/liquidity
- High volume + High LLM confidence → "High"
- Low volume (< 500) → Downgrade to "Low"

**Reason Tags:**
- `stats` — Team/player statistics
- `injury` — Player injury status
- `form` — Recent form/performance
- `news` — Breaking news
- `data` — Historical base-rate data
- `record` — Head-to-head record
- `consensus` — Expert/public consensus
- `volume` — Trading volume signals
- `schedule` — Schedule strength
- `weather` — Weather/field conditions
- `momentum` — Recent momentum swing
- `unclear` — Insufficient information

### Stage 5: Consolidation

**Output Sections:**

1. **Top Picks by Edge** — |Edge| ≥ 5%, ranked by magnitude
2. **Top Picks by EV** — Positive EV, ranked
3. **Markets to Avoid** — No edge or negative EV
4. **Detailed Odds Overview** — Per-market breakdown

---

## Web Search Implementation

### MultiSourceContext

```python
@dataclass
class MultiSourceContext:
    reddit: list[SearchResult]
    yahoo: list[SearchResult]
    espn: list[SearchResult]
    x: list[SearchResult]
    general: list[SearchResult]
    
    def build_context_string(self, anchor: str) -> str:
        # Format as structured markdown for LLM
```

### Parallel Execution

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # Submit all searches concurrently
    future_to_source = {}
    for source, queries in source_queries.items():
        for query in queries:
            future = executor.submit(_brave_search_source, query, source)
            future_to_source[future] = source
    
    # Collect results as they complete
    for future in concurrent.futures.as_completed(future_to_source):
        source = future_to_source[future]
        results = future.result()
        # Aggregate by source
```

---

## Metrics Calculation

### Edge

**Definition:** Difference between LLM-estimated true probability and market-implied probability.

```
Edge = LLM% - Market%

Example:
  Market YES price: 65¢ → Implied: 65%
  LLM YES estimate: 72%
  Edge = 72% - 65% = +7%
```

**Interpretation:**
- Positive edge → Market underestimates probability (potential value)
- Negative edge → Market overestimates probability (avoid)
- Zero edge → Market is efficient

### Expected Value (EV)

**Definition:** Expected profit per cent invested.

```
EV/c = Edge

Example (continued):
  Edge: +7%
  EV/c = +0.07
  
  For $1 wager:
  Expected return = $1 + $0.07 = $1.07
  Expected profit = $0.07 per $1
```

**Edge Threshold:** 5% (0.05) minimum for recommendations

### Return on Investment (ROI)

**Definition:** Percentage return relative to investment.

```
ROI = (EV / MarketPrice) × 100

Example:
  EV/c: +0.07
  Market YES price: 65¢ = $0.65
  ROI = (0.07 / 0.65) × 100 = +10.8%
```

**Note:** ROI can be very high for low-probability outcomes (e.g., +224% for 8¢ → 25¢)

---

## Report Generation

### Terminal Output (8 Sections)

1. **Header**
   - Title: "CONSOLIDATED MARKET REPORT"
   - Timestamp, market count, model, mode

2. **Summary Table** (30 markets)
   - Columns: Market, Best Edge, Best EV, Sentiment, ROI, Rec, Conf, Why

3. **Top Picks by Edge** (|Edge| ≥ 5%)
   - Ranked by |Edge| descending
   - Shows: Rank, Market, Edge%, Volume, Rec, Conf

4. **Top Picks by EV** (Positive EV)
   - Ranked by EV descending
   - Shows: Rank, Market, EV/c, ROI%, Rec, Volume

5. **Markets to Avoid**
   - Edge < 5% or negative EV

6. **Mini Odds Overview** (per market)
   - Table: Outcome | Market% | LLM% | Edge | EV/c | ROI
   - Color-coded cells for positive/negative edge

7. **Why Column Legend**
   - Explanation of all 12 reason tags

8. **Footer** (verbose mode)
   - Detailed web research context

### PDF Output

**Features:**
- Same 8 sections as terminal
- Professional styling with brand colors
- Color-coded cells:
  - Green background: Positive edge (≥ 5%)
  - Red background: Negative edge (≤ -5%)
  - Green text: BUY recommendation
  - Red text: SELL recommendation
- Page break before detailed odds section

**File Naming:**
- Single market: `reports/YYYY-MM-DD/{ticker}.pdf`
- Consolidated: `reports/YYYY-MM-DD/consolidated_{HHMMSS}.pdf`

---

## CLI Interface

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `TICKER` | str | Exact market ticker (positional) |
| `--search QUERY` | str | Search markets by keyword |
| `--date YYYY-MM-DD` | date | Filter by game date |
| `--pick N` | int | Top N markets by volume |
| `--limit N` | int | Max markets to display (default: 10) |
| `--min-volume N` | int | Minimum volume filter |
| `--min-open-interest N` | int | Minimum OI filter |
| `--exclude-started / --no-exclude-started` | bool | Filter started games |
| `--sports SPORT [SPORT...]` | list | Filter by sport category |
| `--llm` | flag | Enable LLM analysis |
| `--provider {claude,kimi,moonshot}` | str | LLM provider |
| `--model MODEL` | str | Override default model |
| `--deep-research` | flag | Run 5-stage pipeline |
| `--web-search` | flag | Enable multi-source web search |
| `--edge-threshold FLOAT` | float | Edge threshold (default: 0.05) |
| `--pdf` | flag | Save PDF report |
| `--verbose` | flag | Show detailed context |
| `--summary` | flag | Quick summary only |

### Usage Patterns

```bash
# Quick volume summary
uv run python -m kalshi_sports_edge --pick 20 --summary

# Single sport analysis
uv run python -m kalshi_sports_edge --pick 10 --sports soccer --deep-research

# Multi-sport with web search and PDF
uv run python -m kalshi_sports_edge --pick 15 --sports basketball soccer tennis \
    --deep-research --web-search --pdf

# Specific date analysis
uv run python -m kalshi_sports_edge --date 2026-03-15 --sports basketball \
    --deep-research --web-search --verbose

# Search with LLM
uv run python -m kalshi_sports_edge --search "Lakers" --llm --web-search
```

---

## Extension Points

### Adding a New Sport

1. **Add series tickers to config.py:**
```python
NEW_SPORT_SERIES: list[str] = [
    "KXNEWSERIES1",
    "KXNEWSERIES2",
]
```

2. **Register in SPORT_CATEGORIES:**
```python
SPORT_CATEGORIES: dict[str, list[str]] = {
    # ... existing sports
    "new_sport": NEW_SPORT_SERIES,
}
```

3. **Update SUPPORTED_SPORTS list**

### Adding a New Web Source

1. **Add source to web_search.py:**
```python
source_queries = {
    # ... existing sources
    'new_source': [
        f"site:newsource.com {base_query}",
    ],
}
```

2. **Update MultiSourceContext:**
```python
@dataclass
class MultiSourceContext:
    # ... existing sources
    new_source: list[SearchResult] = field(default_factory=list)
```

### Adding a New Report Section

1. **Update terminal.py:**
   - Add function `_print_new_section()`
   - Call from `print_enhanced_consolidated_report()`

2. **Update pdf_report.py:**
   - Add function `_build_new_section()`
   - Call from `write_enhanced_consolidated_report()`

### Custom Metrics

To add new metrics, extend `MarketAnalysis` dataclass and update calculation in `deep_research.py`:

```python
# In models.py
@dataclass
class MarketAnalysis:
    # ... existing fields
    new_metric: float

# In deep_research.py
def _analyze_all_markets(...):
    # ... existing calculations
    analysis.new_metric = calculate_new_metric(...)
```

---

## Environment Variables

### Required for Basic Operation
```bash
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=kalshi.pem
KALSHI_ENV=demo  # or "prod"
```

### Required for Web Search
```bash
BRAVE_SEARCH_API_KEY=your-brave-key
```

### Required for LLM Analysis
```bash
ANTHROPIC_API_KEY=your-key      # --provider claude
KIMI_API_KEY=your-key           # --provider kimi
MOONSHOT_API_KEY=your-key       # --provider moonshot
```

---

## Dependencies

```toml
[project.dependencies]
rich = ">=13.0.0"           # Terminal output
reportlab = ">=4.0.0"       # PDF generation
httpx = ">=0.27.0"          # HTTP client
openai = ">=1.0.0"          # OpenAI SDK (Moonshot)
anthropic = ">=0.30.0"      # Anthropic SDK (Claude, Kimi)
pdfplumber = ">=0.11.0"     # PDF processing (optional)
```

---

## File Reference

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `cli.py` | CLI parsing | `CLIArgs`, `parse_args()` |
| `config.py` | Configuration | `SPORT_CATEGORIES`, series lists |
| `models.py` | Data models | `MarketData`, `OddsTable`, `MarketAnalysis` |
| `orchestrator.py` | Main coordinator | `run()`, `_run_deep_research()` |
| `terminal.py` | Terminal output | `print_enhanced_consolidated_report()` |
| `pdf_report.py` | PDF generation | `write_enhanced_consolidated_report()` |
| `deep_research.py` | Analysis pipeline | `run_deep_research()`, 5 stages |
| `web_search.py` | Web search | `search_game_context()`, `MultiSourceContext` |
| `market_fetcher.py` | Market fetching | `fetch_top_n()`, `_fetch_all_sports_markets()` |
| `odds_engine.py` | Odds calculations | `calc_market_odds()` |
| `llm_pipeline.py` | Single-pass LLM | `run_single_pass()` |
| `market_utils.py` | Utilities | `group_markets_by_game()` |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No markets found | Check `--no-exclude-started` or try different `--date` |
| Web search fails | Verify `BRAVE_SEARCH_API_KEY` |
| LLM auth error | Check provider API key env var |
| PDF generation fails | Ensure `reportlab` is installed |
| Slow fetching | Reduce `--limit` or use `--sports` filter |

### Debug Mode

Use `--verbose` to see:
- Detailed web search results
- LLM prompts and responses
- Stage-by-stage progress

---

*Last updated: 2026-02-23*
*Version: 2.0*
