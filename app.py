"""
AI SIFI Monitor — tracking 45 systemically important AI infrastructure players.

Thesis: like pre-2008 financial institutions, the AI infra stack has interlocking
obligations, concentration risk, off-balance-sheet leverage (SPV data centers),
and confidence-sensitive demand. Failure of one node — NVIDIA GPU supply,
OpenAI revenue, Virginia power grid, Taiwan Strait, rare earth embargo — cascades
through all tiers. Unlike bank recapitalizations, compute infrastructure takes
5–10 years to rebuild.
"""

import streamlit as st

from data.sidebar import tier_selector
from data.styles import CUSTOM_CSS
from tabs import news, portfolio, stack, vintage

st.set_page_config(
    page_title="AI SIFI Monitor",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject dark SIFI theme CSS once, up top
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Shared sidebar — tier selector is persistent across all tabs
selected_tier = tier_selector()

st.markdown(
    "<h1 style='margin-bottom:0.2rem;'>AI SIFI Monitor</h1>"
    "<p style='color:#94A3B8; font-size:0.95rem; margin-top:0; max-width:1100px;'>"
    "Surveillance framework for the AI compute buildout. "
    "Tracks balance-sheet leverage, off-balance-sheet SPV commitments, "
    "vendor-financing circularity, and single-source dependencies across "
    "the 45 institutions whose simultaneous stress would re-rate the entire stack. "
    "Fundamentals, flagged news events, and intra-tier dispersion feed a composite "
    "risk score intended to lead — not follow — the market's repricing of the thesis."
    "</p>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs([
    "Portfolio Overview",
    "Vintage Analysis",
    "News & Risk Monitor",
    "Stack Comparison",
])

with tab1:
    portfolio.render(selected_tier)

with tab2:
    vintage.render()

with tab3:
    news.render()

with tab4:
    stack.render()
