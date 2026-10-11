[README.md](https://github.com/user-attachments/files/33308058/README.md)
# AI SIFI Monitor

**Surveillance framework for the AI compute buildout — 45 institutions, 8 interlocking tiers.**

Streamlit dashboard that applies the pre-2008 **Systemically Important Financial Institution (SIFI)** framing to the AI infrastructure stack. Tracks balance-sheet leverage, off-balance-sheet SPV commitments, vendor-financing circularity, and single-source dependencies across the companies whose simultaneous stress would re-rate the entire theme.

Live code: `https://github.com/Ann100182/ai-sifi-monitor`

---

## Thesis

Pre-2008, a small number of banks held interlocking obligations that no single balance sheet made visible. The AI compute buildout now exhibits the same pattern:

- **Concentration** — four semiscalers (NVIDIA, TSMC, ASML, Broadcom) and four hyperscalers (Microsoft, Alphabet, Amazon, Meta) are ~20% of developed-world equity market cap, up from ~5% seven years ago.
- **Off-balance-sheet leverage** — Meta's $27B Hyperion SPV with Blue Owl functions as a de facto triple-net lease but doesn't consolidate onto Meta's credit metrics under current rating-agency treatment.
- **Vendor circularity** — NVIDIA invests in neoclouds that rent GPUs back to its enterprise customers; Oracle has committed to deliver $60B/yr of compute to OpenAI, which doesn't yet earn that much revenue.
- **Single-source dependencies** — TSMC manufactures ~90% of leading-edge logic; ASML holds a monopoly on EUV lithography; Virginia hosts ~67 GW of planned data center capacity against a grid that added only 25 GW nationally in 2024 (derated).

Unlike bank recapitalizations, recovery from compute infrastructure collapse has a 5–10 year rebuild timeline. This dashboard tracks the 45 institutions at the center of that chain and the leading indicators of stress — valuation extremes, credit spread widening, capacity price surges, news-cited risk events — so position sizing can lead rather than follow the market's repricing of the thesis.

Source material: Michael Cembalest, *JPM 2026 Outlook* ("Smothering Heights") and Lindsay Tyler et al., *Morgan Stanley Thoughts on the Market* (data center financing podcast, March 2026).

---

## The 8-tier stack

| Tier | Layer | Count | Representative players |
|---|---|---|---|
| 1 | Power Generation (Utilities) | 8 | Constellation, Vistra, NextEra, Entergy |
| 2 | Grid & Electrical Capital Equipment | 6 | GE Vernova, Eaton, Quanta, Trane |
| 3 | Semi Equipment & EDA | 2 | ASML, Cadence |
| 4 | Semi Design | 7 | NVIDIA, AMD, Broadcom, Micron |
| 5 | Semi Manufacturing | 1 | TSMC |
| 6 | AI Hardware & Networking | 4 | Super Micro, Dell, Arista |
| 7 | Hyperscalers & Cloud | 7 | Microsoft, Alphabet, Amazon, Meta, Oracle, CoreWeave |
| 8 | AI Software, Apps & Security | 10 | Palantir, ServiceNow, Palo Alto Networks |

Composite risk scoring currently flags **4 Critical** (NVDA, TSM, ORCL, CRWV), **13 Elevated**, **18 Watch**, **10 Normal**.

---

## Features — 4 tabs

### 1. Portfolio Overview
Risk × Investment Matrix for every player — status badge (Critical / Elevated / Watch / Normal), 10-point risk score, 10-point opportunity score, one-line bull factor. Sidebar tier browser lets you drill into any of the 8 layers; each tier view carries a thesis one-liner, status counts, and expandable live Yahoo Finance fundamentals (market cap, YTD, 52W, forward P/E, FCF margin, Net Debt / EBITDA).

### 2. Vintage Analysis
"If I had put $10,000 into each of the top 10 by market cap 5 / 10 / 15 years ago…" — per-ticker end value, CAGR, max drawdown, and a line chart of normalized growth. Multiselect lets you override the top-10 default with any subset of the 45.

### 3. News & Risk Monitor
Per-ticker RSS via Google News (aggregates Bloomberg, WSJ, Reuters, FT) plus direct Bloomberg Markets / Technology / Opinion feeds. Every headline is tagged against an 11-theme SIFI risk taxonomy and severity-weighted — the aggregate score re-ranks the portfolio by news-flagged risk. Flagged headlines are shown with 🔴🟡🟢 markers for severity.

### 4. Stack Comparison
Intra-tier dispersion — best and worst performer per tier on YTD return, FCF margin, leverage, and valuation. Highlights where the laggard is a safety signal (crowded, low-dispersion tier) versus a warning (concentrated, high-impact tier like Semi Manufacturing).

---

## Risk-scoring methodology

Each player carries two hand-tuned 10-point scores sourced from Cembalest's WCGW analysis:

- **Risk /10** — cascade potential weighted by tier severity + leverage profile + concentration + known vendor dependencies. TSMC = 10 (Taiwan Strait single-point-of-failure); NVDA / ORCL / CRWV = 9; NiSource / HP / Fortinet = 4.
- **Invest /10** — risk-adjusted opportunity: moat strength + growth runway + relative valuation. Not a buy recommendation — a relative ranking within this SIFI universe.

The News tab layers a **news risk score** on top: for every recent headline it detects, keyword matching against 11 themes (Taiwan / TSMC, China sanctions, US power grid, GPU oversupply, OpenAI concentration, SPV leverage, rare earths, helium/water, AI ROI skepticism, antitrust, nuclear/SMR delays) adds severity weight (1-3) to a per-ticker total. The composite re-ranks the Portfolio tab so recent news stress is reflected in the standings.

The 11 risk themes and their keyword triggers live in `data/risks.py` and are intended to be edited as the thesis evolves.

---

## Quickstart

```bash
git clone https://github.com/Ann100182/ai-sifi-monitor.git
cd ai-sifi-monitor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501.

First load pulls fundamentals from Yahoo Finance for all 45 tickers and 30-ish per-ticker news feeds — expect ~30-60 seconds. All data is cached (1 hour for fundamentals, 30 min for news, 6 hours for 15-year price history).

---

## Project structure

```
ai-sifi-monitor/
├── app.py                      # 4-tab Streamlit entry, injects global CSS
├── requirements.txt            # streamlit, yfinance, pandas, plotly, feedparser
├── .streamlit/config.toml      # dark theme
├── data/
│   ├── players.py              # 45-player universe + 8-tier taxonomy + risk/invest scores
│   ├── risks.py                # 11-theme SIFI risk taxonomy + keyword triggers
│   ├── tier_meta.py            # per-tier icon + description for the sidebar
│   ├── sidebar.py              # shared left-sidebar tier nav
│   └── styles.py               # custom dark CSS + HTML widgets (badges, bars, pills)
└── tabs/
    ├── portfolio.py            # Tab 1: Risk × Investment Matrix
    ├── vintage.py              # Tab 2: $10K vintage analysis
    ├── news.py                 # Tab 3: News & Risk Monitor
    └── stack.py                # Tab 4: Stack Comparison
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| UI | Streamlit | Fast financial dashboards with native dark theme and tabs |
| Market data | yfinance | Free, no API key, batched price + fundamentals |
| News | feedparser + Google News / Bloomberg RSS | Free, no API keys, aggregates premium sources per ticker |
| Charts | Plotly | Interactive, inherits dark theme, built-in strip/bar/line |

Python 3.9+. All dependencies in `requirements.txt`.

---

## Data sources

- **Prices & fundamentals** — Yahoo Finance via `yfinance`
- **Per-ticker news** — Google News RSS (aggregates Bloomberg, WSJ, Reuters, FT, CNBC)
- **Broad sector news** — Bloomberg Markets / Technology / Politics / Opinion RSS
- **Thesis & player universe** — JPM 2026 Outlook (M. Cembalest); Morgan Stanley Thematic Research (L. Tyler on data center financing)

---

## Roadmap

- **SPV / off-balance-sheet debt tracker** — scrape 10-K disclosures for operating leases, residual value guarantees, project-finance obligations (Meta-Hyperion template, Intel-Brookfield, Oracle-Stargate)
- **Options skew monitor** — tail-risk pricing for the 4 critical nodes (NVDA / TSM / ORCL / CRWV)
- **Capacity price feeds** — PJM / ERCOT auction prices as a leading indicator for Tier 1 stress
- **Credit spread integration** — 5Y CDS deltas for ORCL / META / INTC
- **Satellite imagery hooks** — data center construction progress (Planet Labs / Umbra)
- **Export control news scrapers** — real-time BIS Entity List additions, Dutch export rulings

---

## Attribution

Thesis built from:

- Cembalest, M. *Smothering Heights: is the largest moat in market history indestructible?* JPM 2026 Outlook, January 2026.
- Tyler, L., Byrd, S., Baer, J. *Welcome to Part Two of Thoughts on the Market: Financing AI.* Morgan Stanley, March 2026.
- *The State of AI in Business 2025.* MIT NANDA, July 2025.
- *Accountable Acceleration: Gen AI Fast-Tracks into the Enterprise.* Wharton Human-AI Research, October 2025.
- *Monitoring Analytics State of the Market Report for PJM.* November 2025.

Dashboard scaffolded with Claude Code.

---

## License

MIT — see `LICENSE` (add one if you want others to be able to fork cleanly).
