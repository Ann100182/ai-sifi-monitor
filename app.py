"""
AI SIFI Monitor — tracking 45 systemically important AI infrastructure players.

Thesis: like pre-2008 financial institutions, the AI infra stack has interlocking
obligations, concentration risk, off-balance-sheet leverage (SPV data centers),
and confidence-sensitive demand. Failure of one node — NVIDIA GPU supply,
OpenAI revenue, Virginia power grid, Taiwan Strait, rare earth embargo — cascades
through all tiers. Unlike bank recapitalizations, compute infrastructure takes
5–10 years to rebuild.
"""

from pathlib import Path

import streamlit as st

from data.hero import hero
from data.players import PLAYERS
from data.sidebar import tier_selector
from data.styles import CUSTOM_CSS
from tabs import exposureiq, news, portfolio, stack, vintage

st.set_page_config(
    page_title="AI SIFI Monitor",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

selected_tier = tier_selector()

# Top-of-app masthead
st.markdown(
    "<div style='padding: 0.4rem 0 0.2rem 0;'>"
    "<h1 style='margin:0; font-size:1.9rem; letter-spacing:-0.01em;'>AI SIFI Monitor</h1>"
    "<p style='color:#94A3B8; font-size:0.9rem; margin:0.2rem 0 0.6rem 0; max-width:1100px;'>"
    "Surveillance framework for the AI compute buildout. Tracks concentration risk, "
    "off-balance-sheet leverage, vendor-financing circularity, and single-source "
    "dependencies across 45 systemically important institutions."
    "</p></div>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Portfolio Overview",
    "📈  Vintage Analysis",
    "📡  News & Risk Monitor",
    "🏗️  Stack Comparison",
    "🔎  ExposureIQ",
])

# ---- Portfolio ----
with tab1:
    hero(
        theme="portfolio",
        icon="🎯",
        title="Portfolio Overview",
        tagline=(
            "Risk × Investment matrix across every player in the universe. Status badges, "
            "severity-weighted risk scores, and one-line bull-case factors — "
            "sortable by tier via the sidebar."
        ),
        chips=[
            ("Players", f"{len(PLAYERS)}"),
            ("Tiers", "8"),
            ("Universe", "US + EU + TW"),
            ("Updated", "live via Yahoo Finance"),
        ],
    )
    portfolio.render(selected_tier)

# ---- Vintage ----
with tab2:
    hero(
        theme="vintage",
        icon="📈",
        title="Vintage Analysis",
        tagline=(
            "If you had invested $10,000 in each of the top-10 players five, ten, or "
            "fifteen years ago — what would you be sitting on today? CAGR, max drawdown, "
            "and growth paths per ticker."
        ),
        chips=[
            ("Vintages", "5 / 10 / 15 yr"),
            ("Default universe", "Top-10 by market cap"),
            ("Source", "Yahoo Finance adj-close"),
        ],
    )
    vintage.render()

# ---- News & Risk Monitor ----
with tab3:
    hero(
        theme="news",
        icon="📡",
        title="News & Risk Monitor",
        tagline=(
            "Bloomberg + Google News feeds, per-ticker and sector-wide. Every headline "
            "is tagged against the 11-theme SIFI risk taxonomy; severity weights roll up "
            "into a dynamic re-ranking of the portfolio."
        ),
        chips=[
            ("Themes tracked", "11"),
            ("Sources", "Bloomberg · Google News · Reuters · CNBC"),
            ("Refresh", "30 min cache"),
        ],
    )
    news.render()

# ---- Stack Comparison ----
with tab4:
    hero(
        theme="stack",
        icon="🏗️",
        title="Stack Comparison",
        tagline=(
            "Intra-tier dispersion across the 8-layer AI compute stack — "
            "who's leading and who's lagging on return, FCF margin, leverage, and "
            "valuation inside each layer of the chain."
        ),
        chips=[
            ("Tiers", "8"),
            ("Dispersion", "YTD return per ticker"),
            ("Drilldowns", "best + worst per metric"),
        ],
    )
    stack.render()

# ---- ExposureIQ (new, Phase 4/5 GraphRAG) ----
with tab5:
    st.image(str(Path(__file__).parent / "assets" / "exposureiq_banner.png"), width="stretch")
    hero(
        theme="exposureiq",
        icon="🔎",
        title="ExposureIQ",
        tagline=(
            "GraphRAG over 147 SEC filings (10-K · 10-Q · 20-F · DEF 14A) from 12 cloud peers. "
            "Surfaces hidden leverage, circularity, revenue roundtripping, SPV debt, and "
            "capex ROI gaps that balance sheets don't show — with verbatim citations."
        ),
        chips=[
            ("Filings indexed", "147"),
            ("Risk signals", "1,801"),
            ("Companies", "12"),
            ("Backend", "LangGraph · Kuzu + Chroma · Sonnet 4.6 / Opus 4.7"),
        ],
    )
    exposureiq.render()
